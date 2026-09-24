from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.dataset_preprocessing import (
    DATA_QUALITY_FILENAME,
    CLEAN_PRODUCTS_FILENAME,
    CLEAN_SALES_FILENAME,
    REJECTED_SALES_FILENAME,
    build_cleaning_summary,
    build_data_quality_table,
    build_source_profile,
    clean_product_list,
    clean_sales,
    export_cleaned_outputs,
    validate_exported_outputs,
)


def sample_products() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "EntrNo": [1, 2],
            "EntrName": ["Bajaj CT125", "Bike B"],
            "EntrDetails": ["Commuter / 125cc", "Sport / 400cc"],
            "Manufacturing Date": [2022, 2023],
            "Acquisiton": [2023, 2024],
            "UnitPrice": [67_900, 300_000],
        }
    )


def sample_sales() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": ["7/22/2025", "08-10-2025", "08-11-2025"],
            "client_type": ["Retail", "Wholesale", "Retail"],
            "product": ["Bajaj CT12x", "Bike B", "Bike B"],
            "unitprice": [203_700, 300_000, 300_000],
            "quantity": [2, 3, 1],
            "total": [135_800, 900_000, 300_000],
            "payment": ["Cash", "Card", None],
        }
    )


class DatasetExportTests(unittest.TestCase):
    def _export_sample(self, export_dir: Path) -> dict[str, Path]:
        products = sample_products()
        sales = sample_sales()
        profile = build_source_profile(products, sales)
        clean_products = clean_product_list(products)
        clean_sales_records, rejected_sales = clean_sales(sales, clean_products)
        summary = build_cleaning_summary(
            sales,
            clean_products,
            clean_sales_records,
            rejected_sales,
            profile,
        )
        quality = build_data_quality_table(profile, summary)
        return export_cleaned_outputs(
            clean_products,
            clean_sales_records,
            rejected_sales,
            quality,
            export_dir,
        )

    def test_exports_and_round_trip_validates_all_four_csv_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            export_dir = Path(temporary_directory)
            paths = self._export_sample(export_dir)

            self.assertEqual(
                paths["clean_products"].name, CLEAN_PRODUCTS_FILENAME
            )
            self.assertEqual(paths["clean_sales"].name, CLEAN_SALES_FILENAME)
            self.assertEqual(
                paths["rejected_sales"].name, REJECTED_SALES_FILENAME
            )
            self.assertEqual(paths["data_quality"].name, DATA_QUALITY_FILENAME)
            validate_exported_outputs(paths, 2, 2, 1)

            exported_sales = pd.read_csv(paths["clean_sales"], dtype=str)
            self.assertTrue(
                exported_sales["Date"].str.fullmatch(r"\d{4}-\d{2}-\d{2}").all()
            )
            rejected = pd.read_csv(paths["rejected_sales"])
            self.assertEqual(rejected.loc[0, "Source Row Number"], 4)
            self.assertEqual(
                rejected.loc[0, "Rejection Reasons"], "Missing payment method"
            )

    def test_round_trip_validation_detects_a_tampered_total(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            paths = self._export_sample(Path(temporary_directory))
            exported_sales = pd.read_csv(paths["clean_sales"])
            exported_sales.loc[0, "Total"] = 1
            exported_sales.to_csv(paths["clean_sales"], index=False)

            with self.assertRaisesRegex(ValueError, "totals"):
                validate_exported_outputs(paths, 2, 2, 1)


if __name__ == "__main__":
    unittest.main()
