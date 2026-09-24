from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from src.dataset_preprocessing import (
    DEFAULT_DATA_DIR,
    analyze_inventory,
    clean_product_list,
    load_sources,
    validate_inventory_analysis,
)


class InventoryAnalysisTests(unittest.TestCase):
    def test_calculates_required_descriptive_statistics(self) -> None:
        products = pd.DataFrame(
            {
                "Product ID Number": pd.Series([1, 2, 3], dtype="Int64"),
                "Product Name": ["Bike A", "Bike B", "Bike C"],
                "Product Type": ["Scooter", "Sport", "Scooter"],
                "Unit Price": pd.Series([100_000, 200_000, 300_000], dtype="Int64"),
                "Date of Manufacturing": pd.Series(
                    [2021, 2022, 2022], dtype="Int64"
                ),
                "Date of Acquisition": pd.Series([2022, 2023, 2024], dtype="Int64"),
            }
        )

        analysis = analyze_inventory(products)

        self.assertEqual(analysis["total_products"], 3)
        self.assertEqual(analysis["total_product_types"], 2)
        self.assertEqual(
            analysis["product_type_counts"], {"Scooter": 2, "Sport": 1}
        )
        self.assertEqual(analysis["unit_price_statistics_php"]["mean"], 200_000)
        self.assertEqual(
            analysis["unit_price_statistics_php"]["total_inventory_cost"],
            600_000,
        )
        self.assertEqual(
            analysis["manufacturing_year_counts"], {"2021": 1, "2022": 2}
        )
        self.assertEqual(
            analysis["acquisition_lag_year_counts"], {"1": 2, "2": 1}
        )
        validate_inventory_analysis(analysis)


@unittest.skipUnless(
    (Path(DEFAULT_DATA_DIR) / "MotorPH_Products_List_2025.csv").is_file(),
    "Local assignment sources are not available",
)
class InventoryAnalysisIntegrationTests(unittest.TestCase):
    def test_real_product_analysis_matches_reviewed_results(self) -> None:
        source_products, _ = load_sources(DEFAULT_DATA_DIR)
        analysis = analyze_inventory(clean_product_list(source_products))
        prices = analysis["unit_price_statistics_php"]

        self.assertEqual(analysis["total_products"], 50)
        self.assertEqual(analysis["total_product_types"], 17)
        self.assertEqual(analysis["product_type_counts"]["Scooter"], 12)
        self.assertEqual(analysis["product_type_counts"]["Naked bike"], 7)
        self.assertEqual(prices["mean"], 257_872)
        self.assertEqual(prices["median"], 204_950)
        self.assertEqual(prices["minimum"], 48_000)
        self.assertEqual(prices["maximum"], 995_000)
        self.assertEqual(prices["total_inventory_cost"], 12_893_600)
        self.assertEqual(
            analysis["manufacturing_year_counts"],
            {"2020": 5, "2021": 8, "2022": 16, "2023": 21},
        )
        self.assertEqual(
            analysis["acquisition_year_counts"],
            {"2021": 5, "2022": 7, "2023": 17, "2024": 21},
        )
        self.assertEqual(analysis["acquisition_lag_year_counts"], {"1": 49, "2": 1})


if __name__ == "__main__":
    unittest.main()
