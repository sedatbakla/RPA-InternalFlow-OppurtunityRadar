"""Tests for opportunity, risk, and priority score calculations."""

from __future__ import annotations

import unittest

import pandas as pd

from scoring import score_flows


def build_scoring_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return a small deterministic scoring fixture."""
    flows = pd.DataFrame(
        {
            "Flow ID": [1, 2],
            "Flow Name": ["Flow A", "Flow B"],
            "Customer": ["Alpha", "Beta"],
            "Department": ["IT", "Finance"],
            "Capability": ["Original A", "Original B"],
            "Run Count": [100, 50],
            "Error Rate": [1, 5],
            "Manual Time": [20, 10],
            "Transaction Volume": [200, 100],
        }
    )
    classifications = pd.DataFrame(
        {
            "Flow ID": [1, 2],
            "Predicted Capability": ["Shared", "Shared"],
            "Matched Keyword": ["flow", "flow"],
        }
    )
    return flows, classifications


class ScoringTests(unittest.TestCase):
    """Verify deterministic formulas and scoring contracts."""

    def test_scores_match_expected_formula(self) -> None:
        flows, classifications = build_scoring_inputs()
        result = score_flows(flows, classifications).set_index("Flow ID")

        self.assertEqual(result.loc[1, "Customer Count"], 2)
        self.assertEqual(result.loc[2, "Customer Count"], 2)
        self.assertAlmostEqual(result.loc[1, "Opportunity Score"], 98.0)
        self.assertAlmostEqual(result.loc[2, "Opportunity Score"], 46.0)
        self.assertAlmostEqual(result.loc[1, "Priority Score"], 46.0)
        self.assertAlmostEqual(result.loc[2, "Priority Score"], 50.0)
        self.assertEqual(result.loc[1, "Opportunity Level"], "High")
        self.assertEqual(result.loc[2, "Priority Level"], "High")

    def test_mismatched_classification_ids_are_rejected(self) -> None:
        flows, classifications = build_scoring_inputs()
        classifications.loc[1, "Flow ID"] = 3

        with self.assertRaisesRegex(ValueError, "IDs do not match"):
            score_flows(flows, classifications)

    def test_negative_numeric_values_are_rejected(self) -> None:
        flows, classifications = build_scoring_inputs()
        flows.loc[0, "Run Count"] = -1

        with self.assertRaisesRegex(ValueError, "cannot contain negative"):
            score_flows(flows, classifications)


if __name__ == "__main__":
    unittest.main()
