import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from ushd import LifeTableInput, build_life_table, decompose_between_counties, horiuchi_decomposition


class DecompositionTests(unittest.TestCase):
    def test_build_life_table_monotonic_lx(self):
        table = build_life_table(
            LifeTableInput(
                age_lower=[0, 1, 5],
                age_upper=[1, 5, None],
                mx=[0.005, 0.0008, 0.02],
            )
        )
        lx = table.lx
        self.assertTrue(all(lx[i + 1] <= lx[i] for i in range(len(lx) - 1)))
        self.assertGreater(table.ex[0], table.ex[1])

    def test_horiuchi_decomposition_matches_direct_difference(self):
        age_lower = [0, 1, 5]
        age_upper = [1, 5, None]
        county_a_mx = [0.005, 0.0008, 0.02]
        county_b_mx = [0.006, 0.001, 0.018]

        result = horiuchi_decomposition(
            baseline_mx=county_a_mx,
            comparison_mx=county_b_mx,
            age_lower=age_lower,
            age_upper=age_upper,
        )

        table_a = build_life_table(
            LifeTableInput(age_lower=age_lower, age_upper=age_upper, mx=county_a_mx)
        )
        table_b = build_life_table(
            LifeTableInput(age_lower=age_lower, age_upper=age_upper, mx=county_b_mx)
        )
        diff = table_b.ex[0] - table_a.ex[0]
        total = sum(result.contribution)
        self.assertLess(abs(total - diff), 1e-3)

    def test_decompose_between_counties_round_trip(self):
        records = [
            {"county": "A", "race": "White", "sex": "Female", "age_lower": 0, "age_upper": 1, "mx": 0.005},
            {"county": "A", "race": "White", "sex": "Female", "age_lower": 1, "age_upper": 5, "mx": 0.0008},
            {"county": "A", "race": "White", "sex": "Female", "age_lower": 5, "age_upper": None, "mx": 0.02},
            {"county": "B", "race": "White", "sex": "Female", "age_lower": 0, "age_upper": 1, "mx": 0.006},
            {"county": "B", "race": "White", "sex": "Female", "age_lower": 1, "age_upper": 5, "mx": 0.001},
            {"county": "B", "race": "White", "sex": "Female", "age_lower": 5, "age_upper": None, "mx": 0.018},
        ]

        contributions = decompose_between_counties(
            records,
            county_col="county",
            race_col="race",
            sex_col="sex",
            age_lower_col="age_lower",
            age_upper_col="age_upper",
            mx_col="mx",
            county_a="A",
            county_b="B",
            race="White",
            sex="Female",
        )

        total_gap = contributions[0]["life_expectancy_difference"]
        self.assertLess(abs(sum(row["contribution"] for row in contributions) - total_gap), 1e-3)
        for row in contributions:
            self.assertEqual(row["county_a"], "A")
            self.assertEqual(row["county_b"], "B")
            self.assertEqual(row["race"], "White")
            self.assertEqual(row["sex"], "Female")


if __name__ == "__main__":
    unittest.main()
