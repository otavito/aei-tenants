# AEI Tenants Tree Dashboard

This project provides a **single-page web application** that visualizes the AEI tenant structure in a hierarchical tree.

The structure displayed in the tree is:

Tenant → Site → Building

The page also displays **summary indicators** such as total tenants, sites, buildings, and predominant software versions.

---

# Components

## 1. Web Application (Tree Dashboard)

The web page renders:

* A **top section** with KPI indicators
* A **bottom section** containing the interactive tree

The tree allows:

* Expanding / collapsing tenants and sites
* Viewing metadata such as:

  * Total sites per tenant
  * Total buildings per tenant/site
  * Contact information
  * Software versions per building

The tree is rendered using **D3.js**.

Data is loaded from:

```
aei_tenants_d3.json
```

---

## 2. Python Script (Data Builder)

The file:

```
build_tree_json.py
```

converts the raw dataset into the hierarchical JSON format used by the dashboard.

Input dataset format:

```
TENANT
SITE
BUILDING
INTREGRA VERSION
INTRAE VERSION
CONTACT
```

Example:

```
ROSE ACRES | GUTHRIE CENTER | HOUSE 13 |  | INTRATOUCH 3.54 | Kris Randol...
```

The script automatically calculates:

### Global indicators

* total_tenants
* total_sites
* total_buildings
* intrae_predominant_version
* integra_predominant_version

### Per tenant

* total_sites
* total_buildings

### Per site

* total_buildings

---

# Updating the Data

When the dataset changes:

### 1. Update the Excel or CSV dataset

Replace the source file used by the script:

```
base.xlsx
```

or

```
base.csv
```

Ensure the column headers remain:

```
TENANT
SITE
BUILDING
INTREGRA VERSION
INTRAE VERSION
CONTACT
```

---

### 2. Run the Python script

```
python build_tree_json.py
```

or

```
py build_tree_json.py
```

---

### 3. JSON file will be regenerated

The script produces:

```
aei_tenants_d3.json
```

This file is automatically used by the web application.

No changes to the web code are required.

---

# Dependencies

Python packages required:

```
pandas
openpyxl
```

Install once with:

```
pip install pandas openpyxl
```

---

# Workflow Summary

1. Update the dataset (Excel/CSV)
2. Run the Python script
3. The JSON file is regenerated
4. Refresh the web page

The dashboard will display the updated structure automatically.
