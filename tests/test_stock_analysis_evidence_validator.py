import importlib.util
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = (
    REPO_ROOT
    / ".agents"
    / "skills"
    / "run-stock-analysis-graph"
    / "scripts"
    / "validate_evidence.py"
)
SPEC = importlib.util.spec_from_file_location("stock_analysis_evidence_validator", VALIDATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class EvidenceValidatorTests(unittest.TestCase):
    def load_fixture(self, name: str):
        path = REPO_ROOT / "evals" / "cases" / name
        return json.loads(path.read_text(encoding="utf-8"))

    def test_valid_fixture_passes(self):
        result = VALIDATOR.validate_artifact(self.load_fixture("valid-stock-analysis.json"))

        self.assertTrue(result["valid"])
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["metrics"]["scenario_count"], 3)

    def test_schema_1_1_requires_analyst_report(self):
        artifact = self.load_fixture("valid-stock-analysis.json")
        del artifact["analyst_report"]

        result = VALIDATOR.validate_artifact(artifact)

        self.assertFalse(result["valid"])
        self.assertIn("analyst_report is required", "\n".join(result["errors"]))

    def test_analyst_report_rejects_unknown_claim_reference(self):
        artifact = self.load_fixture("valid-stock-analysis.json")
        artifact["analyst_report"]["final_assessment"]["claim_ids"] = ["unknown"]

        result = VALIDATOR.validate_artifact(artifact)

        self.assertFalse(result["valid"])
        self.assertIn("contains unknown ids: unknown", "\n".join(result["errors"]))

    def test_invalid_fixture_is_rejected_by_multiple_gates(self):
        result = VALIDATOR.validate_artifact(self.load_fixture("invalid-stock-analysis.json"))

        self.assertFalse(result["valid"])
        combined = "\n".join(result["errors"])
        self.assertIn("order_action must be 'none'", combined)
        self.assertIn("sources must be a non-empty array", combined)
        self.assertIn("review.verdict must be 'pass'", combined)

    def test_malformed_reference_is_reported_without_crashing(self):
        artifact = self.load_fixture("valid-stock-analysis.json")
        artifact["claims"][0]["source_ids"] = [{"unexpected": "object"}]

        result = VALIDATOR.validate_artifact(artifact)

        self.assertFalse(result["valid"])
        self.assertIn("must contain only non-empty string ids", "\n".join(result["errors"]))


if __name__ == "__main__":
    unittest.main()
