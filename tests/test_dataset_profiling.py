from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from src.dataset_preprocessing import (
    DEFAULT_DATA_DIR,
    load_sources,
    profile_product_list,
    profile_sales,
)


class ProductProfileTests(unittest.TestCase):
    def test_profiles_product_ids_prices_and_types(self) -> None:
        products = pd.DataFrame(
            {
                "EntrNo": [1, 2],
                "EntrName": ["Bike A", "Bike B"],
                "EntrDetails": ["Scooter / 100cc", "Sport / 400cc"],
                "Manufacturing Date": [2022, 2023],
                "Acquisiton": [2023, 2024],
                "UnitPrice": [100_000, 300_000],
            }
        )

        profile = profile_product_list(products)

        self.assertEqual(profile["row_count"], 2)
        self.assertTrue(profile["product_ids_are_sequential"])
        self.assertEqual(profile["unit_price_mean"], 200_000.0)
        self.assertEqual(profile["product_type_counts"], {"Scooter": 1, "Sport": 1})


class SalesProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.products = pd.DataFrame(
            {
                "EntrNo": [1, 2],
                "EntrName": ["Bajaj CT125", "Bike B"],
                "EntrDetails": ["Commuter / 125cc", "Sport / 400cc"],
                "Manufacturing Date": [2022, 2023],
                "Acquisiton": [2023, 2024],
                "UnitPrice": [67_900, 300_000],
            }
        )

    def test_profiles_reviewed_name_and_price_corrections(self) -> None:
        sales = pd.DataFrame(
            {
                "date": ["7/22/2025", "08-10-2025", "2025/07/32"],
                "client_type": ["Retail", "Wholesale", "Retail"],
                "product": ["Bajaj CT12x", "Bike B", "Bike B"],
                "unitprice": [203_700, 300_000, 300_000],
                "quantity": [2, 1, 1],
                "total": [135_800, 300_000, 300_000],
                "payment": ["Cash", "Transfer", "Cash"],
            }
        )

        profile = profile_sales(sales, self.products)

        self.assertEqual(profile["date_parse_failures"], 1)
        self.assertEqual(profile["corrected_product_name_rows"], 1)
        self.assertEqual(profile["catalog_unit_price_mismatch_rows"], 1)
        self.assertEqual(profile["catalog_total_mismatch_rows"], 0)
        self.assertEqual(profile["projected_clean_row_count"], 2)


@unittest.skipUnless(
    (Path(DEFAULT_DATA_DIR) / "MotorPH_Products_List_2025.csv").is_file(),
    "Local assignment sources are not available",
)
class SourceIntegrationTests(unittest.TestCase):
    def test_source_profile_matches_reviewed_counts(self) -> None:
        products, sales = load_sources(DEFAULT_DATA_DIR)
        product_profile = profile_product_list(products)
        sales_profile = profile_sales(sales, products)

        self.assertEqual(product_profile["row_count"], 50)
        self.assertEqual(product_profile["duplicate_rows"], 0)
        self.assertTrue(product_profile["product_ids_are_sequential"])
        self.assertEqual(sales_profile["row_count"], 1_000)
        self.assertEqual(sales_profile["date_parse_failures"], 6)
        self.assertEqual(sales_profile["rows_outside_supplied_period"], 1)
        self.assertEqual(sales_profile["corrected_product_name_rows"], 15)
        self.assertEqual(sales_profile["catalog_unit_price_mismatch_rows"], 20)
        self.assertEqual(sales_profile["catalog_total_mismatch_rows"], 0)
        self.assertEqual(sales_profile["projected_clean_row_count"], 973)


if __name__ == "__main__":
    unittest.main()
