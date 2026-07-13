"""Tests for keyword-based capability classification."""

from __future__ import annotations

import unittest

import pandas as pd

from classifier import classify_flow, classify_flows


class ClassifierTests(unittest.TestCase):
    """Verify matching, fallback, and identifier validation."""

    def setUp(self) -> None:
        self.taxonomy = pd.DataFrame(
            {
                "Keyword": ["invoice", "hire"],
                "Capability": ["Finance", "HR"],
            }
        )

    def test_single_flow_matching_is_case_insensitive(self) -> None:
        capability = classify_flow("INVOICE approval", self.taxonomy)
        self.assertEqual(capability, "Finance")

    def test_batch_classification_preserves_results_and_fallback(self) -> None:
        flows = pd.DataFrame(
            {
                "Flow ID": [1, 2, 3],
                "Flow Name": ["Invoice approval", "New hire", "Archive logs"],
                "Capability": ["Finance", "HR", "IT"],
            }
        )

        result = classify_flows(flows, self.taxonomy)

        self.assertListEqual(
            result["Predicted Capability"].tolist(),
            ["Finance", "HR", "Other"],
        )
        self.assertListEqual(
            result["Classification Correct"].tolist(),
            [True, True, False],
        )
        self.assertTrue(pd.isna(result.loc[2, "Matched Keyword"]))

    def test_duplicate_flow_ids_are_rejected(self) -> None:
        flows = pd.DataFrame(
            {
                "Flow ID": [1, 1],
                "Flow Name": ["Invoice approval", "New hire"],
            }
        )

        with self.assertRaisesRegex(ValueError, "Flow IDs must be unique"):
            classify_flows(flows, self.taxonomy)


if __name__ == "__main__":
    unittest.main()
