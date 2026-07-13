"""Tests for customer capability gap recommendations."""

from __future__ import annotations

import unittest

import pandas as pd

from recommendation import RECOMMENDATION_COLUMNS, build_customer_recommendations


def build_recommendation_scores() -> pd.DataFrame:
    """Return a deterministic customer capability portfolio."""
    return pd.DataFrame(
        {
            "Flow ID": [1, 2, 3, 4],
            "Flow Name": [
                "Invoice Automation",
                "Invoice Review",
                "Hiring",
                "Onboarding",
            ],
            "Customer": ["Alpha", "Beta", "Alpha", "Gamma"],
            "Department": ["Finance", "Finance", "HR", "HR"],
            "Capability": ["Finance", "Finance", "HR", "HR"],
            "Opportunity Score": [80, 70, 90, 60],
            "Product Score": [90, 80, 90, 70],
            "Risk Score": [10, 20, 90, 20],
            "Risk Level": ["Low", "Low", "Critical", "Low"],
        }
    )


class RecommendationTests(unittest.TestCase):
    """Verify missing-capability detection and safe references."""

    def test_missing_customer_capabilities_are_recommended(self) -> None:
        result = build_customer_recommendations(build_recommendation_scores())

        self.assertEqual(tuple(result.columns), RECOMMENDATION_COLUMNS)
        self.assertEqual(len(result), 2)
        pairs = set(
            result[["Target Customer", "Recommended Capability"]].itertuples(
                index=False,
                name=None,
            )
        )
        self.assertSetEqual(pairs, {("Beta", "HR"), ("Gamma", "Finance")})
        self.assertTrue(result["Customer Reach"].eq(2).all())

    def test_critical_reference_is_not_selected(self) -> None:
        result = build_customer_recommendations(build_recommendation_scores())
        hr_recommendation = result[result["Recommended Capability"].eq("HR")]

        self.assertEqual(hr_recommendation.iloc[0]["Reference Flow"], "Onboarding")
        self.assertFalse(result["Risk Level"].eq("Critical").any())

    def test_excluding_all_risk_levels_returns_empty_output(self) -> None:
        result = build_customer_recommendations(
            build_recommendation_scores(),
            excluded_risk_levels=("Low", "Critical"),
        )
        self.assertTrue(result.empty)
        self.assertEqual(tuple(result.columns), RECOMMENDATION_COLUMNS)

    def test_out_of_range_scores_are_rejected(self) -> None:
        scores = build_recommendation_scores()
        scores.loc[0, "Opportunity Score"] = 101

        with self.assertRaisesRegex(ValueError, "between 0 and 100"):
            build_customer_recommendations(scores)


if __name__ == "__main__":
    unittest.main()
