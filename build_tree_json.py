import json
import sys
from pathlib import Path

import pandas as pd


# --------- Config ---------
ROOT_NAME = "AEI Tenants"
ROOT_TYPE = "root"

# Aceita cabeçalhos com variações (p.ex. typo "INTREGRA VERSION")
COLUMN_ALIASES = {
    "TENANT": ["TENANT", "Tenant", "CUSTOMER", "Customer"],
    "SITE": ["SITE", "Site"],
    "BUILDING": ["BUILDING", "Building", "HOUSE", "House"],
    "INTEGRA VERSION": ["INTEGRA VERSION", "INTREGRA VERSION", "INTEGRA", "INTEGRAVERSION", "INTEGRA_VERSION"],
    "INTRAE VERSION": ["INTRAE VERSION", "INTRAE", "INTRAEVERSION", "INTRAE_VERSION"],
    "CONTACT": ["CONTACT", "Contact"],
}

# Chaves do JSON (para manter compatível com seu front atual)
JSON_KEYS = {
    "total_tenants": "Total count of tenants",
    "total_sites": "Total count of sites",
    "total_buildings": "total_buildings",
    "intrae_predominant_version": "INTRAE predominant version",
    "integra_predominant_version": "INTEGRA predominant version",
}
# -------------------------


def resolve_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = {c.strip(): c for c in df.columns}
    mapping = {}

    for canonical, variants in COLUMN_ALIASES.items():
        found = None
        for v in variants:
            if v in cols:
                found = cols[v]
                break
        if not found:
            # tenta matching por case-insensitive
            for c in df.columns:
                if str(c).strip().lower() == v.strip().lower():
                    found = c
                    break
        if not found:
            raise ValueError(f"Coluna obrigatória não encontrada: {canonical}. Colunas atuais: {list(df.columns)}")
        mapping[canonical] = found

    # renomeia para canônico
    df = df.rename(columns={mapping[k]: k for k in mapping})
    return df[list(mapping.keys())]


def clean_str(s):
    if pd.isna(s):
        return ""
    return str(s).strip()


def predominant(series: pd.Series) -> str:
    s = series.dropna().map(clean_str)
    s = s[s != ""]
    if s.empty:
        return ""
    # moda (valor mais frequente)
    return s.value_counts().idxmax()


def pick_contact(group: pd.DataFrame) -> str:
    # escolhe o contato mais frequente (ignora vazio)
    s = group["CONTACT"].dropna().map(clean_str)
    s = s[s != ""]
    if s.empty:
        return ""
    return s.value_counts().idxmax()


def load_input(path: Path) -> pd.DataFrame:
    ext = path.suffix.lower()
    if ext in [".csv"]:
        # tenta detectar separador automaticamente
        try:
            return pd.read_csv(path, sep=None, engine="python")
        except Exception:
            # fallback comum
            return pd.read_csv(path)
    if ext in [".xlsx", ".xls"]:
        return pd.read_excel(path)
    raise ValueError("Formato não suportado. Use .csv ou .xlsx/.xls")


def main():
    if len(sys.argv) < 3:
        print("Uso: python build_tree_json.py <input.csv|xlsx> <output.json>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    df = load_input(input_path)
    df = resolve_columns(df)

    # limpeza básica
    for c in df.columns:
        df[c] = df[c].map(clean_str)

    # remove linhas sem tenant/site/building (se existirem)
    df = df[(df["TENANT"] != "") & (df["SITE"] != "") & (df["BUILDING"] != "")].copy()

    # indicadores gerais
    total_tenants = df["TENANT"].nunique()
    total_sites = df.drop_duplicates(["TENANT", "SITE"]).shape[0]
    total_buildings = df.drop_duplicates(["TENANT", "SITE", "BUILDING"]).shape[0]

    intrae_pred = predominant(df["INTRAE VERSION"])
    integra_pred = predominant(df["INTEGRA VERSION"])

    root = {
        "name": ROOT_NAME,
        "type": ROOT_TYPE,
        JSON_KEYS["total_tenants"]: int(total_tenants),
        JSON_KEYS["total_sites"]: int(total_sites),
        JSON_KEYS["total_buildings"]: int(total_buildings),
        JSON_KEYS["intrae_predominant_version"]: intrae_pred,
        JSON_KEYS["integra_predominant_version"]: integra_pred,
        "children": [],
    }

    # ordenação opcional (fica mais previsível)
    df = df.sort_values(["TENANT", "SITE", "BUILDING"])

    # construir hierarquia
    tenant_nodes = []

    # construir hierarquia
    tenant_nodes = []

    for tenant, tenant_df in df.groupby("TENANT", sort=False):
        tenant_sites = tenant_df.drop_duplicates(["TENANT", "SITE"]).shape[0]
        tenant_buildings = tenant_df.drop_duplicates(["TENANT", "SITE", "BUILDING"]).shape[0]

        tenant_node = {
            "name": tenant,
            "type": "customer",
            "total_sites": int(tenant_sites),
            "total_buildings": int(tenant_buildings),
            "children": [],
        }

        for site, site_df in tenant_df.groupby("SITE", sort=False):
            site_buildings = site_df.drop_duplicates(["TENANT", "SITE", "BUILDING"]).shape[0]
            contact = pick_contact(site_df)

            site_node = {
                "name": site,
                "type": "site",
                "total_buildings": int(site_buildings),
                "children": [],
                "contact": contact,
            }

            bcols = ["TENANT", "SITE", "BUILDING", "INTEGRA VERSION", "INTRAE VERSION"]
            bdf = site_df[bcols].copy()

            def mode_nonempty(s: pd.Series) -> str:
                s = s.dropna().map(clean_str)
                s = s[s != ""]
                if s.empty:
                    return ""
                return s.value_counts().idxmax()

            bgroup = bdf.groupby(["TENANT", "SITE", "BUILDING"], sort=False).agg({
                "INTEGRA VERSION": mode_nonempty,
                "INTRAE VERSION": mode_nonempty,
            }).reset_index()

            for _, row in bgroup.iterrows():
                building_node = {
                    "name": row["BUILDING"],
                    "type": "building",
                }
                if row["INTEGRA VERSION"]:
                    building_node["integra_version"] = row["INTEGRA VERSION"]
                if row["INTRAE VERSION"]:
                    building_node["intrae_version"] = row["INTRAE VERSION"]

                site_node["children"].append(building_node)

            tenant_node["children"].append(site_node)

        tenant_nodes.append(tenant_node)

    # ordenar tenants pelo número de buildings (decrescente)
    tenant_nodes.sort(key=lambda x: x["total_buildings"], reverse=True)
    root["children"] = tenant_nodes

    # salva
    output_path.write_text(json.dumps(root, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"OK: JSON gerado em {output_path}")
    print(f"- tenants: {total_tenants} | sites: {total_sites} | buildings: {total_buildings}")
    print(f"- INTRAE predominant: {intrae_pred or '(empty)'}")
    print(f"- INTEGRA predominant: {integra_pred or '(empty)'}")

if __name__ == "__main__":
    main()