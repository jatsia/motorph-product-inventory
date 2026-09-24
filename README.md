# MotorPH Product Inventory

This project prepares and analyzes the supplied MotorPH product and sales data for the MO-IT106 Milestone 1 Product Inventory Report. The work will use a small pandas-based preprocessing script, reproducible data-quality checks, cleaned CSV outputs, and the supplied Word report template.

## Current status

The required preprocessing, validated exports, inventory analysis, and six-page report are complete. The learner and program fields have been filled in the local report without recording those personal details in this README. Rejected sales records retain their original fields, source row numbers, and explicit reasons. No source row or source template has been modified.

The original files are retained locally under `references/` and excluded from Git. This is important because the supplied report template states that it must not be distributed or uploaded.

## Source materials

```text
references/
|-- data/
|   |-- MotorPH_Products_List_2025.csv
|   `-- MotorPH_Sales Data-3rd Quarter-Year 2025 (1).csv
|-- instructions/
|   |-- e2T9AoRP.jpg
|   `-- gNpcZ2Kv.jpg
`-- template/
    `-- Copy of MO-IT106 Milestone 1_ MotorPH Product Inventory Report _SECTION_ _LAST NAME, M.I_.docx
```

## Initial source audit

### Product list

- 50 product records and 6 columns.
- No missing values, blank text, duplicate rows, or duplicate product IDs.
- Product IDs are sequential from 1 through 50.
- Manufacturing years run from 2020 through 2023.
- Acquisition years run from 2021 through 2024.
- Unit prices range from PHP 48,000 to PHP 995,000, with a mean of PHP 257,872.
- Column names do not match the required report format.
- Product type must be extracted from the category before `/` in `EntrDetails`.

Required output order:

1. Product ID Number
2. Product Name
3. Product Type
4. Unit Price
5. Date of Manufacturing
6. Date of Acquisition

### Sales data

- 1,000 records and 7 columns.
- The supplied period is June through August 2025. One parseable record is dated January 13, 2025 and falls outside that period.
- Six dates are missing or impossible after mixed-format parsing.
- Ten records have no client type, and ten different records have no payment type.
- Thirteen distinct product-name variants affect 15 rows and can be mapped back to catalog products.
- Twenty rows contain a unit price three times the catalog price. Their recorded totals already equal catalog price multiplied by quantity, so the catalog price is the defensible correction.
- There are no duplicate rows, non-positive quantities, or non-positive prices.

The sales data is supporting evidence for preprocessing. The report template's required inventory analysis is based primarily on the cleaned 50-row product list.

## Lean implementation plan

### Phase 1  Preserve and profile the sources

- [x] Load both CSVs with pandas without overwriting them.
- [x] Record row counts, columns, data types, nulls, duplicates, category values, date coverage, and arithmetic checks.
- [x] Keep all cleaning rules explicit in code instead of manually editing CSV cells.

### Phase 2  Build one preprocessing script

- [x] Create `src/dataset_preprocessing.py` as the single required Python deliverable.
- [x] Normalize column names and text whitespace.
- [x] Convert numeric and date fields deliberately.
- [x] Apply a reviewed mapping for the 13 malformed sales product labels.
- [x] Use the product catalog as the authoritative unit-price lookup.
- [x] Retain excluded sales rows in memory with their original values and explicit reasons.
- [x] Validate row counts, sequential product IDs, required columns, valid years, catalog matches, and `total == unit price * quantity`.

### Phase 3  Export clean datasets

- [x] Export the required six-column product list CSV with all 50 catalog records.
- [x] Export a cleaned sales CSV for the supplied June-August 2025 period.
- [x] Exclude records that cannot be repaired without inventing a date, client type, or payment type.
- [x] Preserve every excluded record in an audit CSV with its source row number and rejection reason.
- [x] Save data-quality counts alongside the outputs so the report can describe the actual work performed.
- [x] Reload and validate all four exported CSV files independently.

Expected cleaned sales count under this policy: 973 rows. This is 1,000 source rows less 6 invalid or missing dates, 1 out-of-period date, 10 missing client types, and 10 missing payment types; these issue groups do not overlap.

### Phase 4  Perform descriptive analysis

- [x] Calculate total products and counts by product type.
- [x] Calculate mean, median, quartiles, minimum, maximum, and range for unit price.
- [x] Calculate total inventory cost as the sum of one listed unit price per catalog product, matching the report template's inventory definition.
- [x] Review manufacturing and acquisition-year patterns.
- [x] Keep the report focused on statistics and findings that directly support the assignment.

### Phase 5  Complete the report template

- [x] Preserve the supplied template layout and replace only its instructional placeholder text.
- [x] Complete the introduction, objectives, scope, methodology, analysis, observations, findings, and appendices from verified outputs.
- [x] Include three findings tied directly to reported statistics.
- [x] Add the learner name and program only after those details are supplied.
- [x] Render and inspect all six report pages before submission.

### Phase 6  Package and verify the submission

- [x] Arrange the `.py` file and cleaned `.csv` files in the required `Milestone 1/Dataset Preprocessing` submission structure.
- [x] Add the completed report and any approved supporting tables or charts.
- [x] Run the preprocessing script from a clean environment and compare its output with the documented counts.
- Check links and Google Drive permissions manually before submission.

## Planned project structure

```text
motorph-product-inventory/
|-- src/
|   `-- dataset_preprocessing.py
|-- tests/
|   |-- test_dataset_cleaning.py
|   |-- test_dataset_exports.py
|   |-- test_dataset_profiling.py
|   `-- test_inventory_analysis.py
|-- references/              # Local only; ignored by Git
|-- outputs/                 # Generated locally; ignored by Git
|   |-- cleaned/             # Clean product and sales CSVs
|   |-- audit/               # Rejected records and quality counts
|   |-- analysis/            # Verified descriptive statistics
|   `-- report/              # Completed and rendered report
|-- submission/              # Personal/course submission; ignored by Git
|-- .gitignore
|-- AGENTS.md                # Local guidance; ignored by Git
`-- README.md
```

Create implementation folders only when that phase begins. This keeps the repository small and avoids placeholder code.

## Run the current preprocessing checks

Create a Python environment and install pandas:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Generate the profiles and all four CSV outputs without changing either source CSV:

```sh
python src/dataset_preprocessing.py
```

The command writes:

- `outputs/cleaned/MotorPH_Product_List_Cleaned_2025.csv`
- `outputs/cleaned/MotorPH_Sales_Cleaned_Quarter_3_2025.csv`
- `outputs/audit/MotorPH_Sales_Rejected_Rows_Quarter_3_2025.csv`
- `outputs/audit/MotorPH_Data_Quality_Summary.csv`
- `outputs/source_profile.json`
- `outputs/cleaning_summary.json`
- `outputs/analysis/inventory_analysis.json`
- `outputs/report/Sia-MotorPH_Product_Inventory_Report_Quarter_3_2025.docx`

After writing the CSVs, the script reloads them and rechecks schemas, row counts, dates, catalog prices, sales arithmetic, rejected-record traceability, and quality counts. It then validates and writes the descriptive inventory analysis. All generated outputs are ignored by Git.

Run the profiling tests with:

```sh
python -m unittest discover -s tests -v
```

## Details still needed

- Section and required final filename.
- Confirmation that the instructor treats June-August 2025 as the supplied third-quarter period.
- Google Drive links and sharing permissions, which must be handled at submission time.
