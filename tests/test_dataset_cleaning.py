from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from src.dataset_preprocessing import (
    DEFAULT_DATA_DIR,
    PRODUCT_NAME_CORRECTIONS,
    PRODUCT_OUTPUT_COLUMNS,
    SALES_OUTPUT_COLUMNS,
    build_cleaning_summary,
    build_source_profile,
    clean_product_list,
    clean_sales,
    load_sources,
    validate_clean_product_list,
    validate_clean_sales,
)


def sample_products() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "EntrNo": [1, 2],
            "EntrName": [" Bajaj CT125 ", "Bike B"],
            "EntrDetails": ["Commuter / 125cc", " Sport / 400cc"],
            "Manufacturing Date": [2022, 2023],
            "Acquisiton": [2023, 2024],
            "UnitPrice": [67_900, 300_000],
        }
    )


class ProductCleaningTests(unittest.TestCase):
    def test_builds_required_product_report_format(self) -> None:
        cleaned = clean_product_list(sample_products())

        self.assertEqual(list(cleaned.columns), PRODUCT_OUTPUT_COLUMNS)
        self.assertEqual(cleaned["Product Name"].tolist(), ["Bajaj CT125", "Bike B"])
        self.assertEqual(cleaned["Product Type"].tolist(), ["Commuter", "Sport"])
        validate_clean_product_list(cleaned, expected_row_count=2)

    def test_removes_exact_duplicate_product_rows(self) -> None:
        products = pd.concat(
            [sample_products(), sample_products().iloc[[1]]], ignore_index=True
        )

        cleaned = clean_product_list(products)

        self.assertEqual(len(cleaned), 2)
        validate_clean_product_list(cleaned, expected_row_count=2)


class SalesCleaningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clean_products = clean_product_list(sample_products())

    def test_corrects_valid_rows_and_preserves_rejection_reasons(self) -> None:
        sales = pd.DataFrame(
            {
                "date": [
                    "7/22/2025",
                    "2025/07/32",
                    "1/13/2025",
                    "08-10-2025",
                ],
                "client_type": [" Retail ", "Retail", "Retail", "Wholesale"],
                "product": ["Bajaj CT12x", "Bike B", "Bike B", "Bike B"],
                "unitprice": [203_700, 300_000, 300_000, 300_000],
                "quantity": [2, 1, 1, 3],
                "total": [135_800, 300_000, 300_000, 900_000],
                "payment": [" Cash ", "Cash", "Cash", None],
            }
        )

        cleaned, rejected = clean_sales(sales, self.clean_products)

        self.assertEqual(list(cleaned.columns), SALES_OUTPUT_COLUMNS)
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned.loc[0, "Product Name"], "Bajaj CT125")
        self.assertEqual(cleaned.loc[0, "Unit Price"], 67_900)
        self.assertEqual(cleaned.loc[0, "Total"], 135_800)
        self.assertEqual(cleaned.loc[0, "Client Type"], "Retail")
        self.assertEqual(cleaned.loc[0, "Payment Method"], "Cash")
        self.assertEqual(len(rejected), 3)
        self.assertEqual(rejected["Source Row Number"].tolist(), [3, 4, 5])
        self.assertIn("Invalid or missing date", rejected.loc[0, "Rejection Reasons"])
        self.assertIn("Outside supplied", rejected.loc[1, "Rejection Reasons"])
        self.assertIn("Missing payment method", rejected.loc[2, "Rejection Reasons"])
        validate_clean_sales(cleaned, self.clean_products, expected_row_count=1)

    def test_validation_rejects_tampered_total(self) -> None:
        sales = pd.DataFrame(
            {
                "Date": [pd.Timestamp("2025-07-22")],
                "Client Type": ["Retail"],
                "Product Name": ["Bajaj CT125"],
                "Unit Price": pd.Series([67_900], dtype="Int64"),
                "Quantity": pd.Series([2], dtype="Int64"),
                "Total": pd.Series([1], dtype="Int64"),
                "Payment Method": ["Cash"],
            }
        )

        with self.assertRaisesRegex(ValueError, "totals"):
            validate_clean_sales(sales, self.clean_products)

    def test_summary_separates_source_issues_from_retained_corrections(self) -> None:
        source_sales = pd.DataFrame(
            {
                "date": ["7/22/2025", "2025/07/32"],
                "client_type": ["Retail", "Retail"],
                "product": ["Bajaj CT12x", "Bajaj CT12x"],
                "unitprice": [203_700, 203_700],
                "quantity": [2, 1],
                "total": [135_800, 67_900],
                "payment": ["Cash", "Cash"],
            }
        )
        clean_sales_records, rejected_sales = clean_sales(
            source_sales, self.clean_products
        )
        source_profile = build_source_profile(sample_products(), source_sales)

        summary = build_cleaning_summary(
            source_sales,
            self.clean_products,
            clean_sales_records,
            rejected_sales,
            source_profile,
        )

        self.assertEqual(summary["sales"]["product_name_issue_rows_in_source"], 2)
        self.assertEqual(
            summary["sales"]["product_name_corrections_in_clean_data"], 1
        )
        self.assertEqual(summary["sales"]["unit_price_issue_rows_in_source"], 2)
        self.assertEqual(
            summary["sales"]["unit_price_corrections_in_clean_data"], 1
        )


@unittest.skipUnless(
    (Path(DEFAULT_DATA_DIR) / "MotorPH_Products_List_2025.csv").is_file(),
    "Local assignment sources are not available",
)
class SourceCleaningIntegrationTests(unittest.TestCase):
    def test_real_sources_produce_reviewed_phase_2_counts(self) -> None:
        products, sales = load_sources(DEFAULT_DATA_DIR)
        clean_products = clean_product_list(products)
        clean_sales_records, rejected_sales = clean_sales(sales, clean_products)

        validate_clean_product_list(clean_products, expected_row_count=50)
        validate_clean_sales(
            clean_sales_records, clean_products, expected_row_count=973
        )
        self.assertEqual(len(rejected_sales), 27)
        self.assertEqual(len(PRODUCT_NAME_CORRECTIONS), 13)
        self.assertTrue(
            set(PRODUCT_NAME_CORRECTIONS.values()).issubset(
                set(clean_products["Product Name"])
            )
        )
        self.assertEqual(
            clean_sales_records["Product Name"].nunique(), 50
        )
        self.assertTrue(
            (
                clean_sales_records["Total"]
                == clean_sales_records["Unit Price"]
                * clean_sales_records["Quantity"]
            ).all()
        )


if __name__ == "__main__":
    unittest.main()
