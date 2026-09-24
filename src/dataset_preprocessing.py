"""Profile, clean, export, and validate the MotorPH assignment datasets.

The script keeps the original CSV files read-only, records every rejected sales
row with a reason, and reloads all generated CSV files for independent checks.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "references" / "data"
DEFAULT_PROFILE_OUTPUT = PROJECT_ROOT / "outputs" / "source_profile.json"
DEFAULT_CLEANING_SUMMARY_OUTPUT = PROJECT_ROOT / "outputs" / "cleaning_summary.json"
DEFAULT_ANALYSIS_OUTPUT = PROJECT_ROOT / "outputs" / "analysis" / "inventory_analysis.json"
DEFAULT_EXPORT_DIR = PROJECT_ROOT / "outputs"

CLEAN_PRODUCTS_FILENAME = "MotorPH_Product_List_Cleaned_2025.csv"
CLEAN_SALES_FILENAME = "MotorPH_Sales_Cleaned_Quarter_3_2025.csv"
REJECTED_SALES_FILENAME = "MotorPH_Sales_Rejected_Rows_Quarter_3_2025.csv"
DATA_QUALITY_FILENAME = "MotorPH_Data_Quality_Summary.csv"

PRODUCTS_FILENAME = "MotorPH_Products_List_2025.csv"
SALES_FILENAME = "MotorPH_Sales Data-3rd Quarter-Year 2025 (1).csv"

PRODUCT_SOURCE_COLUMNS = [
    "EntrNo",
    "EntrName",
    "EntrDetails",
    "Manufacturing Date",
    "Acquisiton",
    "UnitPrice",
]
SALES_SOURCE_COLUMNS = [
    "date",
    "client_type",
    "product",
    "unitprice",
    "quantity",
    "total",
    "payment",
]

PRODUCT_OUTPUT_COLUMNS = [
    "Product ID Number",
    "Product Name",
    "Product Type",
    "Unit Price",
    "Date of Manufacturing",
    "Date of Acquisition",
]
SALES_OUTPUT_COLUMNS = [
    "Date",
    "Client Type",
    "Product Name",
    "Unit Price",
    "Quantity",
    "Total",
    "Payment Method",
]

SUPPLIED_PERIOD_START = pd.Timestamp("2025-06-01")
SUPPLIED_PERIOD_END = pd.Timestamp("2025-08-31")

# These corrections were reviewed against both product names and catalog prices.
# Later phases will apply this explicit map instead of fuzzy matching records.
PRODUCT_NAME_CORRECTIONS = {
    "Bajaj CT12x": "Bajaj CT125",
    "Benelli 502x": "Benelli 502C",
    "Bristol Bobber 65x": "Bristol Bobber 650",
    "CFMoto 300Sx": "CFMoto 300SR",
    "Honda ADV 16x": "Honda ADV 160",
    "KTM 790 Dukx": "KTM 790 Duke",
    "Kawasaki KLX 23x": "Kawasaki KLX 230",
    "Motorstar Xplorer 250x": "Motorstar Xplorer 250R",
    "Suzuki Raider R150 Fx": "Suzuki Raider R150 Fi",
    "TVS Apache RTR 200 4x": "TVS Apache RTR 200 4V",
    "Yamaha MT-1x": "Yamaha MT-15",
    "Yamaha Serow 25x": "Yamaha Serow 250",
    "Yamaha Sniper 15x": "Yamaha Sniper 155",
}


def load_sources(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the two original CSV files without modifying them."""
    products_path = data_dir / PRODUCTS_FILENAME
    sales_path = data_dir / SALES_FILENAME

    missing_files = [
        str(path) for path in (products_path, sales_path) if not path.is_file()
    ]
    if missing_files:
        raise FileNotFoundError(
            "Missing required source file(s): " + ", ".join(missing_files)
        )

    products = pd.read_csv(products_path)
    sales = pd.read_csv(sales_path)
    _require_columns(products, PRODUCT_SOURCE_COLUMNS, PRODUCTS_FILENAME)
    _require_columns(sales, SALES_SOURCE_COLUMNS, SALES_FILENAME)
    return products, sales


def _require_columns(
    frame: pd.DataFrame, required_columns: list[str], source_name: str
) -> None:
    missing = [column for column in required_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{source_name} is missing required columns: {missing}")


def _missing_or_blank(series: pd.Series) -> pd.Series:
    blank = series.astype("string").str.strip().eq("").fillna(False)
    return series.isna() | blank


def _blank_text_counts(frame: pd.DataFrame) -> dict[str, int]:
    counts: dict[str, int] = {}
    for column in frame.select_dtypes(include=["object", "string"]).columns:
        text = frame[column].astype("string")
        counts[str(column)] = int(
            (frame[column].notna() & text.str.strip().eq("").fillna(False)).sum()
        )
    return counts


def _value_counts(series: pd.Series) -> dict[str, int]:
    values = series.astype("string").fillna("<missing>")
    counts = values.value_counts(dropna=False)
    return {str(key): int(value) for key, value in counts.items()}


def profile_product_list(products: pd.DataFrame) -> dict[str, Any]:
    """Return source-quality findings for the product catalog."""
    _require_columns(products, PRODUCT_SOURCE_COLUMNS, PRODUCTS_FILENAME)

    product_ids = pd.to_numeric(products["EntrNo"], errors="coerce")
    manufacturing_years = pd.to_numeric(
        products["Manufacturing Date"], errors="coerce"
    )
    acquisition_years = pd.to_numeric(products["Acquisiton"], errors="coerce")
    unit_prices = pd.to_numeric(products["UnitPrice"], errors="coerce")
    product_types = (
        products["EntrDetails"].astype("string").str.split("/", n=1).str[0].str.strip()
    )
    expected_ids = list(range(1, len(products) + 1))

    return {
        "row_count": int(len(products)),
        "column_count": int(len(products.columns)),
        "columns": [str(column) for column in products.columns],
        "data_types": {
            str(column): str(dtype) for column, dtype in products.dtypes.items()
        },
        "missing_values": {
            str(column): int(count)
            for column, count in products.isna().sum().items()
        },
        "blank_text_values": _blank_text_counts(products),
        "duplicate_rows": int(products.duplicated().sum()),
        "duplicate_product_ids": int(product_ids.duplicated().sum()),
        "product_id_min": int(product_ids.min()),
        "product_id_max": int(product_ids.max()),
        "product_ids_are_sequential": product_ids.tolist() == expected_ids,
        "manufacturing_year_min": int(manufacturing_years.min()),
        "manufacturing_year_max": int(manufacturing_years.max()),
        "acquisition_year_min": int(acquisition_years.min()),
        "acquisition_year_max": int(acquisition_years.max()),
        "unit_price_min": float(unit_prices.min()),
        "unit_price_mean": float(unit_prices.mean()),
        "unit_price_max": float(unit_prices.max()),
        "product_type_counts": _value_counts(product_types),
    }


def profile_sales(sales: pd.DataFrame, products: pd.DataFrame) -> dict[str, Any]:
    """Return source-quality findings for the sales data."""
    _require_columns(sales, SALES_SOURCE_COLUMNS, SALES_FILENAME)
    _require_columns(products, PRODUCT_SOURCE_COLUMNS, PRODUCTS_FILENAME)

    parsed_dates = pd.to_datetime(sales["date"], format="mixed", errors="coerce")
    outside_period = parsed_dates.notna() & (
        (parsed_dates < SUPPLIED_PERIOD_START) | (parsed_dates > SUPPLIED_PERIOD_END)
    )

    raw_product_names = sales["product"].astype("string").str.strip()
    canonical_product_names = raw_product_names.replace(PRODUCT_NAME_CORRECTIONS)
    catalog_names = products["EntrName"].astype("string").str.strip()
    catalog_name_set = set(catalog_names.dropna())
    catalog_prices = pd.to_numeric(products["UnitPrice"], errors="coerce")
    catalog_price_lookup = pd.Series(
        catalog_prices.to_numpy(), index=catalog_names.to_numpy()
    )
    canonical_unit_prices = canonical_product_names.map(catalog_price_lookup)

    unit_prices = pd.to_numeric(sales["unitprice"], errors="coerce")
    quantities = pd.to_numeric(sales["quantity"], errors="coerce")
    totals = pd.to_numeric(sales["total"], errors="coerce")

    missing_client_type = _missing_or_blank(sales["client_type"])
    missing_payment_type = _missing_or_blank(sales["payment"])
    unmatched_product = ~canonical_product_names.isin(catalog_name_set)
    invalid_quantity = quantities.isna() | quantities.le(0)
    invalid_catalog_price = canonical_unit_prices.isna() | canonical_unit_prices.le(0)
    invalid_total = totals.isna()

    valid_for_cleaning = ~(
        parsed_dates.isna()
        | outside_period
        | missing_client_type
        | missing_payment_type
        | unmatched_product
        | invalid_quantity
        | invalid_catalog_price
        | invalid_total
    )

    comparable_stated_totals = unit_prices.notna() & quantities.notna() & totals.notna()
    stated_total_mismatch = comparable_stated_totals & (
        unit_prices * quantities != totals
    )
    comparable_catalog_totals = (
        canonical_unit_prices.notna() & quantities.notna() & totals.notna()
    )
    catalog_total_mismatch = comparable_catalog_totals & (
        canonical_unit_prices * quantities != totals
    )
    catalog_price_mismatch = unit_prices.notna() & canonical_unit_prices.notna() & (
        unit_prices != canonical_unit_prices
    )

    non_catalog_source_values = raw_product_names[
        ~raw_product_names.isin(catalog_name_set)
    ]
    normalized_unmatched_values = canonical_product_names[unmatched_product]
    valid_months = parsed_dates.dropna().dt.to_period("M").astype(str)

    return {
        "row_count": int(len(sales)),
        "column_count": int(len(sales.columns)),
        "columns": [str(column) for column in sales.columns],
        "data_types": {
            str(column): str(dtype) for column, dtype in sales.dtypes.items()
        },
        "missing_values": {
            str(column): int(count) for column, count in sales.isna().sum().items()
        },
        "blank_text_values": _blank_text_counts(sales),
        "duplicate_rows": int(sales.duplicated().sum()),
        "date_parse_failures": int(parsed_dates.isna().sum()),
        "parsed_date_min": parsed_dates.min().date().isoformat(),
        "parsed_date_max": parsed_dates.max().date().isoformat(),
        "rows_by_month": {
            str(month): int(count)
            for month, count in valid_months.value_counts().sort_index().items()
        },
        "rows_outside_supplied_period": int(outside_period.sum()),
        "missing_or_blank_client_type_rows": int(missing_client_type.sum()),
        "missing_or_blank_payment_rows": int(missing_payment_type.sum()),
        "unique_source_product_names": int(raw_product_names.nunique(dropna=True)),
        "unique_normalized_product_names": int(
            canonical_product_names.nunique(dropna=True)
        ),
        "non_catalog_source_product_names": _value_counts(
            non_catalog_source_values
        ),
        "corrected_product_name_rows": int(
            raw_product_names.isin(PRODUCT_NAME_CORRECTIONS).sum()
        ),
        "unmatched_product_names_after_reviewed_corrections": _value_counts(
            normalized_unmatched_values
        ),
        "nonpositive_quantity_rows": int(quantities.le(0).fillna(False).sum()),
        "nonpositive_stated_unit_price_rows": int(
            unit_prices.le(0).fillna(False).sum()
        ),
        "stated_total_mismatch_rows": int(stated_total_mismatch.sum()),
        "catalog_unit_price_mismatch_rows": int(catalog_price_mismatch.sum()),
        "catalog_total_mismatch_rows": int(catalog_total_mismatch.sum()),
        "projected_excluded_rows": int((~valid_for_cleaning).sum()),
        "projected_clean_row_count": int(valid_for_cleaning.sum()),
    }


def clean_product_list(products: pd.DataFrame) -> pd.DataFrame:
    """Return the product list in the assignment's required six-column format."""
    _require_columns(products, PRODUCT_SOURCE_COLUMNS, PRODUCTS_FILENAME)

    source = products.drop_duplicates().copy()
    cleaned = pd.DataFrame(
        {
            "Product ID Number": pd.to_numeric(source["EntrNo"], errors="coerce"),
            "Product Name": source["EntrName"].astype("string").str.strip(),
            "Product Type": (
                source["EntrDetails"]
                .astype("string")
                .str.split("/", n=1)
                .str[0]
                .str.strip()
            ),
            "Unit Price": pd.to_numeric(source["UnitPrice"], errors="coerce"),
            "Date of Manufacturing": pd.to_numeric(
                source["Manufacturing Date"], errors="coerce"
            ),
            "Date of Acquisition": pd.to_numeric(
                source["Acquisiton"], errors="coerce"
            ),
        }
    )

    integer_columns = [
        "Product ID Number",
        "Unit Price",
        "Date of Manufacturing",
        "Date of Acquisition",
    ]
    cleaned[integer_columns] = cleaned[integer_columns].astype("Int64")
    return cleaned.reset_index(drop=True)


def validate_clean_product_list(
    products: pd.DataFrame, expected_row_count: int | None = None
) -> None:
    """Raise ValueError when a cleaned product list breaks an assignment rule."""
    _ensure(
        list(products.columns) == PRODUCT_OUTPUT_COLUMNS,
        "Clean product columns are missing or out of order.",
    )
    if expected_row_count is not None:
        _ensure(
            len(products) == expected_row_count,
            f"Expected {expected_row_count} clean products, found {len(products)}.",
        )

    _ensure(not products.isna().any().any(), "Clean product data contains nulls.")
    _ensure(
        not products.duplicated().any(), "Clean product data contains duplicate rows."
    )
    _ensure(
        products["Product ID Number"].is_unique,
        "Clean product IDs are not unique.",
    )
    expected_ids = list(range(1, len(products) + 1))
    _ensure(
        products["Product ID Number"].tolist() == expected_ids,
        "Clean product IDs are not sequential from 1.",
    )
    _ensure(
        products["Product Name"].str.strip().ne("").all(),
        "Clean product names contain blank values.",
    )
    _ensure(
        products["Product Type"].str.strip().ne("").all(),
        "Clean product types contain blank values.",
    )
    _ensure(
        products["Unit Price"].gt(0).all(),
        "Clean product prices must be positive.",
    )
    for column in ("Date of Manufacturing", "Date of Acquisition"):
        _ensure(
            products[column].between(1900, 2100).all(),
            f"{column} contains an invalid year.",
        )


def clean_sales(
    sales: pd.DataFrame, clean_products: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Clean valid sales and preserve excluded source rows with reasons."""
    _require_columns(sales, SALES_SOURCE_COLUMNS, SALES_FILENAME)
    validate_clean_product_list(clean_products)

    source = sales.reset_index(drop=True).copy()
    parsed_dates = pd.to_datetime(source["date"], format="mixed", errors="coerce")
    outside_period = parsed_dates.notna() & (
        (parsed_dates < SUPPLIED_PERIOD_START) | (parsed_dates > SUPPLIED_PERIOD_END)
    )

    client_types = source["client_type"].astype("string").str.strip()
    payment_methods = source["payment"].astype("string").str.strip()
    source_product_names = source["product"].astype("string").str.strip()
    canonical_product_names = source_product_names.replace(PRODUCT_NAME_CORRECTIONS)
    quantities = pd.to_numeric(source["quantity"], errors="coerce")
    source_totals = pd.to_numeric(source["total"], errors="coerce")

    catalog_price_lookup = clean_products.set_index("Product Name")["Unit Price"]
    canonical_unit_prices = canonical_product_names.map(catalog_price_lookup)

    duplicate_source_row = source.duplicated(keep="first")
    missing_date = parsed_dates.isna()
    missing_client_type = _missing_or_blank(source["client_type"])
    missing_payment_method = _missing_or_blank(source["payment"])
    missing_product_name = _missing_or_blank(source["product"])
    unmatched_product_name = (
        ~missing_product_name & canonical_unit_prices.isna()
    )
    invalid_quantity = quantities.isna() | quantities.le(0)
    invalid_catalog_price = canonical_unit_prices.isna() | canonical_unit_prices.le(0)
    invalid_total = source_totals.isna()

    rejection_rules = [
        (duplicate_source_row, "Duplicate source row"),
        (missing_date, "Invalid or missing date"),
        (outside_period, "Outside supplied June-August 2025 period"),
        (missing_client_type, "Missing client type"),
        (missing_payment_method, "Missing payment method"),
        (missing_product_name, "Missing product name"),
        (unmatched_product_name, "Unmatched product name"),
        (invalid_quantity, "Invalid quantity"),
        (invalid_catalog_price, "Invalid catalog unit price"),
        (invalid_total, "Missing source total"),
    ]
    rejection_reasons = pd.Series(
        [
            "; ".join(
                label for mask, label in rejection_rules if bool(mask.iloc[row_index])
            )
            for row_index in range(len(source))
        ],
        index=source.index,
        dtype="string",
    )
    rejected_mask = rejection_reasons.ne("")

    cleaned = pd.DataFrame(
        {
            "Date": parsed_dates,
            "Client Type": client_types,
            "Product Name": canonical_product_names,
            "Unit Price": canonical_unit_prices,
            "Quantity": quantities,
            "Total": canonical_unit_prices * quantities,
            "Payment Method": payment_methods,
        }
    ).loc[~rejected_mask, SALES_OUTPUT_COLUMNS]
    cleaned[["Unit Price", "Quantity", "Total"]] = cleaned[
        ["Unit Price", "Quantity", "Total"]
    ].astype("Int64")
    cleaned = cleaned.reset_index(drop=True)

    rejected = source.loc[rejected_mask].copy()
    rejected.insert(0, "Source Row Number", rejected.index + 2)
    rejected["Rejection Reasons"] = rejection_reasons.loc[rejected_mask].to_numpy()
    rejected = rejected.reset_index(drop=True)
    return cleaned, rejected


def validate_clean_sales(
    sales: pd.DataFrame,
    clean_products: pd.DataFrame,
    expected_row_count: int | None = None,
) -> None:
    """Raise ValueError when cleaned sales break a reviewed cleaning rule."""
    _ensure(
        list(sales.columns) == SALES_OUTPUT_COLUMNS,
        "Clean sales columns are missing or out of order.",
    )
    if expected_row_count is not None:
        _ensure(
            len(sales) == expected_row_count,
            f"Expected {expected_row_count} clean sales, found {len(sales)}.",
        )

    _ensure(not sales.isna().any().any(), "Clean sales data contains nulls.")
    _ensure(not sales.duplicated().any(), "Clean sales data contains duplicates.")
    _ensure(
        sales["Date"].between(SUPPLIED_PERIOD_START, SUPPLIED_PERIOD_END).all(),
        "Clean sales contain dates outside the supplied period.",
    )
    _ensure(sales["Quantity"].gt(0).all(), "Clean sales quantities must be positive.")

    catalog_price_lookup = clean_products.set_index("Product Name")["Unit Price"]
    expected_prices = sales["Product Name"].map(catalog_price_lookup).astype("Int64")
    _ensure(
        expected_prices.notna().all(),
        "Clean sales contain a product not found in the catalog.",
    )
    _ensure(
        sales["Unit Price"].equals(expected_prices),
        "Clean sales unit prices do not match the product catalog.",
    )
    expected_totals = (sales["Unit Price"] * sales["Quantity"]).astype("Int64")
    _ensure(
        sales["Total"].equals(expected_totals),
        "Clean sales totals do not equal unit price multiplied by quantity.",
    )


def build_cleaning_summary(
    source_sales: pd.DataFrame,
    clean_products: pd.DataFrame,
    clean_sales_records: pd.DataFrame,
    rejected_sales: pd.DataFrame,
    source_profile: dict[str, Any],
) -> dict[str, Any]:
    """Summarize the reviewed cleaning transformations."""
    reason_counts: dict[str, int] = {}
    for value in rejected_sales["Rejection Reasons"]:
        for reason in str(value).split("; "):
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

    source = source_sales.reset_index(drop=True)
    rejected_source_indexes = set(
        (rejected_sales["Source Row Number"] - 2).astype(int).tolist()
    )
    retained_source_rows = ~source.index.to_series().isin(rejected_source_indexes)
    source_product_names = source["product"].astype("string").str.strip()
    canonical_product_names = source_product_names.replace(PRODUCT_NAME_CORRECTIONS)
    catalog_price_lookup = clean_products.set_index("Product Name")["Unit Price"]
    catalog_prices = canonical_product_names.map(catalog_price_lookup)
    source_prices = pd.to_numeric(source["unitprice"], errors="coerce")
    product_name_issue = source_product_names.isin(PRODUCT_NAME_CORRECTIONS)
    unit_price_issue = source_prices.notna() & catalog_prices.notna() & (
        source_prices != catalog_prices
    )

    sales_profile = source_profile["sales"]
    return {
        "phase": "Phase 2 - Build and validate cleaning transformations",
        "product_list": {
            "source_rows": source_profile["product_list"]["row_count"],
            "clean_rows": int(len(clean_products)),
            "output_columns": PRODUCT_OUTPUT_COLUMNS,
        },
        "sales": {
            "source_rows": sales_profile["row_count"],
            "clean_rows": int(len(clean_sales_records)),
            "rejected_rows": int(len(rejected_sales)),
            "product_name_issue_rows_in_source": int(product_name_issue.sum()),
            "product_name_corrections_in_clean_data": int(
                (product_name_issue & retained_source_rows).sum()
            ),
            "product_name_issue_rows_rejected": int(
                (product_name_issue & ~retained_source_rows).sum()
            ),
            "unit_price_issue_rows_in_source": int(unit_price_issue.sum()),
            "unit_price_corrections_in_clean_data": int(
                (unit_price_issue & retained_source_rows).sum()
            ),
            "unit_price_issue_rows_rejected": int(
                (unit_price_issue & ~retained_source_rows).sum()
            ),
            "rejection_reason_counts": reason_counts,
            "output_columns": SALES_OUTPUT_COLUMNS,
        },
        "final_csv_exports_created": False,
    }


def build_data_quality_table(
    source_profile: dict[str, Any], cleaning_summary: dict[str, Any]
) -> pd.DataFrame:
    """Build a compact, report-ready table of source and cleaning counts."""
    product_profile = source_profile["product_list"]
    sales_profile = source_profile["sales"]
    sales_summary = cleaning_summary["sales"]

    rows = [
        ("Product List", "Source rows", product_profile["row_count"], "Original catalog"),
        ("Product List", "Clean rows", cleaning_summary["product_list"]["clean_rows"], "Exported catalog"),
        ("Product List", "Duplicate source rows", product_profile["duplicate_rows"], "Exact duplicates"),
        ("Sales", "Source rows", sales_profile["row_count"], "Original sales data"),
        ("Sales", "Clean rows", sales_summary["clean_rows"], "Exported valid sales"),
        ("Sales", "Rejected rows", sales_summary["rejected_rows"], "Preserved in the rejected-records CSV"),
        ("Sales", "Invalid or missing date rows", sales_profile["date_parse_failures"], "Rejected"),
        ("Sales", "Outside supplied period rows", sales_profile["rows_outside_supplied_period"], "Rejected"),
        ("Sales", "Missing or blank client type rows", sales_profile["missing_or_blank_client_type_rows"], "Rejected"),
        ("Sales", "Missing or blank payment rows", sales_profile["missing_or_blank_payment_rows"], "Rejected"),
        ("Sales", "Product name issue rows in source", sales_summary["product_name_issue_rows_in_source"], "Reviewed against the catalog"),
        ("Sales", "Product name corrections in clean data", sales_summary["product_name_corrections_in_clean_data"], "Applied with the explicit correction map"),
        ("Sales", "Product name issue rows rejected", sales_summary["product_name_issue_rows_rejected"], "Rejected for another required-field issue"),
        ("Sales", "Unit price issue rows in source", sales_summary["unit_price_issue_rows_in_source"], "Compared with catalog prices"),
        ("Sales", "Unit price corrections in clean data", sales_summary["unit_price_corrections_in_clean_data"], "Catalog price used"),
        ("Sales", "Unit price issue rows rejected", sales_summary["unit_price_issue_rows_rejected"], "Rejected for another required-field issue"),
        ("Sales", "Clean arithmetic mismatch rows", 0, "Validated as Unit Price x Quantity = Total"),
    ]
    return pd.DataFrame(rows, columns=["Dataset", "Metric", "Count", "Notes"])


def export_cleaned_outputs(
    clean_products: pd.DataFrame,
    clean_sales_records: pd.DataFrame,
    rejected_sales: pd.DataFrame,
    data_quality: pd.DataFrame,
    export_dir: Path,
) -> dict[str, Path]:
    """Write the four Phase 3 CSV outputs and return their paths."""
    cleaned_dir = export_dir / "cleaned"
    audit_dir = export_dir / "audit"
    cleaned_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "clean_products": cleaned_dir / CLEAN_PRODUCTS_FILENAME,
        "clean_sales": cleaned_dir / CLEAN_SALES_FILENAME,
        "rejected_sales": audit_dir / REJECTED_SALES_FILENAME,
        "data_quality": audit_dir / DATA_QUALITY_FILENAME,
    }

    clean_products.to_csv(paths["clean_products"], index=False)
    sales_export = clean_sales_records.copy()
    sales_export["Date"] = sales_export["Date"].dt.strftime("%Y-%m-%d")
    sales_export.to_csv(paths["clean_sales"], index=False)
    rejected_sales.to_csv(paths["rejected_sales"], index=False)
    data_quality.to_csv(paths["data_quality"], index=False)
    return paths


def validate_exported_outputs(
    paths: dict[str, Path],
    expected_product_rows: int,
    expected_sales_rows: int,
    expected_rejected_rows: int,
) -> None:
    """Reload and independently validate every generated Phase 3 CSV."""
    expected_keys = {"clean_products", "clean_sales", "rejected_sales", "data_quality"}
    _ensure(set(paths) == expected_keys, "Export path set is incomplete.")
    for path in paths.values():
        _ensure(path.is_file(), f"Expected exported file was not created: {path}")

    exported_products = pd.read_csv(paths["clean_products"])
    product_integer_columns = [
        "Product ID Number",
        "Unit Price",
        "Date of Manufacturing",
        "Date of Acquisition",
    ]
    exported_products[product_integer_columns] = exported_products[
        product_integer_columns
    ].astype("Int64")
    validate_clean_product_list(exported_products, expected_product_rows)

    exported_sales = pd.read_csv(paths["clean_sales"])
    exported_sales["Date"] = pd.to_datetime(
        exported_sales["Date"], format="%Y-%m-%d", errors="raise"
    )
    sales_integer_columns = ["Unit Price", "Quantity", "Total"]
    exported_sales[sales_integer_columns] = exported_sales[
        sales_integer_columns
    ].astype("Int64")
    validate_clean_sales(exported_sales, exported_products, expected_sales_rows)

    exported_rejections = pd.read_csv(paths["rejected_sales"])
    expected_rejection_columns = [
        "Source Row Number",
        *SALES_SOURCE_COLUMNS,
        "Rejection Reasons",
    ]
    _ensure(
        list(exported_rejections.columns) == expected_rejection_columns,
        "Rejected-record columns are missing or out of order.",
    )
    _ensure(
        len(exported_rejections) == expected_rejected_rows,
        f"Expected {expected_rejected_rows} rejected rows, found {len(exported_rejections)}.",
    )
    _ensure(
        exported_rejections["Source Row Number"].is_unique,
        "Rejected-record source row numbers are not unique.",
    )
    _ensure(
        exported_rejections["Rejection Reasons"].astype("string").str.strip().ne("").all(),
        "A rejected record is missing its rejection reason.",
    )

    exported_quality = pd.read_csv(paths["data_quality"])
    _ensure(
        list(exported_quality.columns) == ["Dataset", "Metric", "Count", "Notes"],
        "Data-quality columns are missing or out of order.",
    )
    _ensure(not exported_quality.empty, "Data-quality output is empty.")
    _ensure(
        not exported_quality[["Dataset", "Metric"]].duplicated().any(),
        "Data-quality metrics are not unique within each dataset.",
    )
    for column in ("Dataset", "Metric", "Notes"):
        _ensure(
            exported_quality[column].astype("string").str.strip().ne("").all(),
            f"Data-quality column '{column}' contains a blank value.",
        )
    quality_counts = pd.to_numeric(exported_quality["Count"], errors="coerce")
    _ensure(quality_counts.notna().all(), "Data-quality counts must be numeric.")
    _ensure(
        quality_counts.ge(0).all() & quality_counts.mod(1).eq(0).all(),
        "Data-quality counts must be non-negative whole numbers.",
    )
    metric_counts = {
        (dataset, metric): int(count)
        for dataset, metric, count in zip(
            exported_quality["Dataset"],
            exported_quality["Metric"],
            quality_counts,
        )
    }
    expected_counts = {
        ("Product List", "Clean rows"): expected_product_rows,
        ("Sales", "Source rows"): expected_sales_rows + expected_rejected_rows,
        ("Sales", "Clean rows"): expected_sales_rows,
        ("Sales", "Rejected rows"): expected_rejected_rows,
        ("Sales", "Clean arithmetic mismatch rows"): 0,
    }
    for metric, expected_count in expected_counts.items():
        _ensure(
            metric_counts.get(metric) == expected_count,
            f"Data-quality metric '{metric}' does not equal {expected_count}.",
        )


def analyze_inventory(clean_products: pd.DataFrame) -> dict[str, Any]:
    """Calculate the descriptive inventory statistics required by the report."""
    validate_clean_product_list(clean_products)

    prices = clean_products["Unit Price"]
    type_counts = (
        clean_products.groupby("Product Type", observed=False)
        .size()
        .rename("Count")
        .reset_index()
        .sort_values(["Count", "Product Type"], ascending=[False, True])
    )
    manufacturing_counts = (
        clean_products["Date of Manufacturing"].value_counts().sort_index()
    )
    acquisition_counts = clean_products["Date of Acquisition"].value_counts().sort_index()
    acquisition_lag = (
        clean_products["Date of Acquisition"]
        - clean_products["Date of Manufacturing"]
    ).value_counts().sort_index()

    analysis = {
        "phase": "Phase 4 - Descriptive product inventory analysis",
        "source": CLEAN_PRODUCTS_FILENAME,
        "total_products": int(len(clean_products)),
        "total_product_types": int(clean_products["Product Type"].nunique()),
        "product_type_counts": {
            str(row["Product Type"]): int(row["Count"])
            for _, row in type_counts.iterrows()
        },
        "unit_price_statistics_php": {
            "mean": float(prices.mean()),
            "median": float(prices.median()),
            "minimum": int(prices.min()),
            "maximum": int(prices.max()),
            "range": int(prices.max() - prices.min()),
            "first_quartile": float(prices.quantile(0.25)),
            "third_quartile": float(prices.quantile(0.75)),
            "total_inventory_cost": int(prices.sum()),
            "products_below_200000": int(prices.lt(200_000).sum()),
            "products_at_or_above_500000": int(prices.ge(500_000).sum()),
        },
        "manufacturing_year_counts": {
            str(year): int(count) for year, count in manufacturing_counts.items()
        },
        "acquisition_year_counts": {
            str(year): int(count) for year, count in acquisition_counts.items()
        },
        "acquisition_lag_year_counts": {
            str(years): int(count) for years, count in acquisition_lag.items()
        },
    }
    validate_inventory_analysis(analysis)
    return analysis


def validate_inventory_analysis(analysis: dict[str, Any]) -> None:
    """Raise ValueError when Phase 4 results fail internal reconciliations."""
    total_products = int(analysis["total_products"])
    type_counts = analysis["product_type_counts"]
    price_statistics = analysis["unit_price_statistics_php"]
    manufacturing_counts = analysis["manufacturing_year_counts"]
    acquisition_counts = analysis["acquisition_year_counts"]
    acquisition_lag_counts = analysis["acquisition_lag_year_counts"]

    _ensure(total_products > 0, "Inventory analysis has no products.")
    _ensure(
        len(type_counts) == int(analysis["total_product_types"]),
        "Product-type total does not match the listed categories.",
    )
    for label, counts in (
        ("product type", type_counts),
        ("manufacturing year", manufacturing_counts),
        ("acquisition year", acquisition_counts),
        ("acquisition lag", acquisition_lag_counts),
    ):
        _ensure(
            sum(int(value) for value in counts.values()) == total_products,
            f"The {label} counts do not reconcile to total products.",
        )

    _ensure(
        price_statistics["minimum"]
        <= price_statistics["median"]
        <= price_statistics["maximum"],
        "Unit-price median falls outside the observed range.",
    )
    _ensure(
        price_statistics["minimum"]
        <= price_statistics["mean"]
        <= price_statistics["maximum"],
        "Unit-price mean falls outside the observed range.",
    )
    _ensure(
        price_statistics["range"]
        == price_statistics["maximum"] - price_statistics["minimum"],
        "Unit-price range does not reconcile.",
    )
    _ensure(
        price_statistics["total_inventory_cost"] > 0,
        "Total inventory cost must be positive.",
    )


def _ensure(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def build_source_profile(
    products: pd.DataFrame, sales: pd.DataFrame
) -> dict[str, Any]:
    """Build the complete Phase 1 source profile."""
    return {
        "phase": "Phase 1 - Preserve and profile the sources",
        "source_files": {
            "product_list": PRODUCTS_FILENAME,
            "sales": SALES_FILENAME,
        },
        "supplied_sales_period": {
            "start": SUPPLIED_PERIOD_START.date().isoformat(),
            "end": SUPPLIED_PERIOD_END.date().isoformat(),
        },
        "product_list": profile_product_list(products),
        "sales": profile_sales(sales, products),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Profile, clean, export, and validate the MotorPH CSV files."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing the two source CSV files.",
    )
    parser.add_argument(
        "--profile-output",
        type=Path,
        default=DEFAULT_PROFILE_OUTPUT,
        help="Path for the generated JSON source profile.",
    )
    parser.add_argument(
        "--cleaning-summary-output",
        type=Path,
        default=DEFAULT_CLEANING_SUMMARY_OUTPUT,
        help="Path for the generated Phase 2 cleaning summary.",
    )
    parser.add_argument(
        "--export-dir",
        type=Path,
        default=DEFAULT_EXPORT_DIR,
        help="Directory for the generated cleaned and audit CSV files.",
    )
    parser.add_argument(
        "--analysis-output",
        type=Path,
        default=DEFAULT_ANALYSIS_OUTPUT,
        help="Path for the generated Phase 4 inventory analysis JSON.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    products, sales = load_sources(args.data_dir)
    profile = build_source_profile(products, sales)
    clean_products = clean_product_list(products)
    clean_sales_records, rejected_sales = clean_sales(sales, clean_products)
    validate_clean_product_list(clean_products, expected_row_count=50)
    validate_clean_sales(
        clean_sales_records, clean_products, expected_row_count=973
    )
    cleaning_summary = build_cleaning_summary(
        sales, clean_products, clean_sales_records, rejected_sales, profile
    )
    data_quality = build_data_quality_table(profile, cleaning_summary)
    exported_paths = export_cleaned_outputs(
        clean_products,
        clean_sales_records,
        rejected_sales,
        data_quality,
        args.export_dir,
    )
    validate_exported_outputs(
        exported_paths,
        expected_product_rows=50,
        expected_sales_rows=973,
        expected_rejected_rows=27,
    )
    cleaning_summary["phase"] = "Phase 3 - Export and validate cleaned datasets"
    cleaning_summary["final_csv_exports_created"] = True
    cleaning_summary["exported_files"] = {
        name: str(path.relative_to(PROJECT_ROOT))
        for name, path in exported_paths.items()
    }
    inventory_analysis = analyze_inventory(clean_products)

    args.profile_output.parent.mkdir(parents=True, exist_ok=True)
    args.profile_output.write_text(
        json.dumps(profile, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    args.cleaning_summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.cleaning_summary_output.write_text(
        json.dumps(cleaning_summary, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    args.analysis_output.parent.mkdir(parents=True, exist_ok=True)
    args.analysis_output.write_text(
        json.dumps(inventory_analysis, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    product_profile = profile["product_list"]
    sales_profile = profile["sales"]
    print(f"Source profile written to {args.profile_output}")
    print(
        "Product list: "
        f"{product_profile['row_count']} rows, "
        f"{product_profile['duplicate_rows']} duplicate rows"
    )
    print(
        "Sales: "
        f"{sales_profile['row_count']} source rows, "
        f"{sales_profile['projected_clean_row_count']} projected clean rows, "
        f"{sales_profile['projected_excluded_rows']} projected exclusions"
    )
    print(f"Cleaning summary written to {args.cleaning_summary_output}")
    print("Phase 3 CSV exports:")
    for path in exported_paths.values():
        print(f"- {path}")
    print(
        "Round-trip validation passed: "
        f"{len(clean_products)} clean products, "
        f"{len(clean_sales_records)} clean sales, "
        f"{len(rejected_sales)} rejected sales"
    )
    price_statistics = inventory_analysis["unit_price_statistics_php"]
    print(f"Inventory analysis written to {args.analysis_output}")
    print(
        "Phase 4 analysis: "
        f"{inventory_analysis['total_products']} products, "
        f"{inventory_analysis['total_product_types']} product types, "
        f"PHP {price_statistics['total_inventory_cost']:,.0f} total inventory cost"
    )


if __name__ == "__main__":
    main()
