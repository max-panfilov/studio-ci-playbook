from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from scripts import check_playbook as checks


ROOT = Path(__file__).resolve().parents[1]


class ExampleSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = checks.load_json(ROOT / "schemas" / "examples.schema.json")
        cls.examples = {
            path.name: checks.load_json(path)
            for path in sorted((ROOT / "examples").glob("*.json"))
        }

    def test_public_schema_is_valid(self) -> None:
        Draft202012Validator.check_schema(self.schema)

    def test_expected_examples_exist(self) -> None:
        self.assertEqual(
            {
                "studio-ci.json",
                "release-policy.json",
                "plan.json",
                "request.json",
                "release-manifest.json",
            },
            set(self.examples),
        )

    def test_examples_match_their_public_contracts(self) -> None:
        for name, document in self.examples.items():
            with self.subTest(example=name):
                validator = Draft202012Validator(checks.schema_for_kind(self.schema, document["kind"]))
                validator.validate(document)
                self.assertIs(document["synthetic"], True)
                self.assertIs(document["evidence"], False)

    def test_schema_rejects_evidence_claim(self) -> None:
        document = deepcopy(self.examples["plan.json"])
        document["evidence"] = True
        validator = Draft202012Validator(checks.schema_for_kind(self.schema, "plan"))
        self.assertTrue(list(validator.iter_errors(document)))

    def test_schema_rejects_real_run_id(self) -> None:
        document = deepcopy(self.examples["request.json"])
        document["run_id"] = 1361
        validator = Draft202012Validator(checks.schema_for_kind(self.schema, "request"))
        self.assertTrue(list(validator.iter_errors(document)))

    def test_manifest_is_explicitly_non_evidence(self) -> None:
        document = self.examples["release-manifest.json"]
        self.assertEqual("synthetic-only", document["status"])
        self.assertIs(document["release_authorized"], False)
        self.assertIs(document["production_access"], False)
        self.assertIs(document["scan"]["fresh"], False)
        self.assertEqual("2000-01-01T00:00:00Z", document["scan"]["created_at"])

    def test_duplicate_json_key_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "DUPLICATE_JSON_KEY"):
            checks.load_json_text('{"synthetic": true, "synthetic": false}')

    def test_locked_verification_and_no_private_binary(self) -> None:
        self.assertTrue((ROOT / "uv.lock").exists())
        self.assertEqual([], list(ROOT.rglob("*.pyz")))


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = checks.make_yaml().load(
            (ROOT / "examples" / "gitea-ci.yml").read_text(encoding="utf-8")
        )

    def test_yaml_12_keeps_on_as_string(self) -> None:
        self.assertIn("on", self.workflow)
        self.assertNotIn(True, self.workflow)
        self.assertEqual({"push", "workflow_dispatch"}, set(self.workflow["on"]))

    def test_workflow_has_no_universal_pull_request_trigger(self) -> None:
        self.assertNotIn("pull_request", self.workflow["on"])
        self.assertNotIn("pull_request_target", self.workflow["on"])

    def test_duplicate_yaml_key_is_rejected(self) -> None:
        with self.assertRaises(Exception):
            checks.make_yaml().load("on: [push]\non: [workflow_dispatch]\n")

    def test_hosted_runner_is_rejected(self) -> None:
        document = deepcopy(self.workflow)
        document["jobs"]["scope-plan"]["runs-on"] = "ubuntu-latest"
        errors = checks.validate_workflow_document(document, "negative-test")
        self.assertTrue(any("HOSTED_RUNNER_FORBIDDEN" in error for error in errors))

    def test_schematic_workflow_is_structurally_valid(self) -> None:
        self.assertEqual([], checks.validate_workflow_document(self.workflow, "examples/gitea-ci.yml"))


class MarkdownAndSafetyTests(unittest.TestCase):
    def test_expected_mermaid_blocks(self) -> None:
        for relative, expected in checks.EXPECTED_MERMAID.items():
            with self.subTest(document=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertEqual(expected, text.count("```mermaid"))

    def test_private_path_marker(self) -> None:
        synthetic_path = "/".join(["", "Users", "example", "private"])
        findings = checks.find_safety_markers(synthetic_path)
        self.assertTrue(any("PRIVATE_MARKER" in finding for finding in findings))

    def test_non_placeholder_sha_is_rejected(self) -> None:
        findings = checks.find_safety_markers("a" * 40)
        self.assertIn("<memory>: NON_PLACEHOLDER_GIT_SHA", findings)

    def test_placeholder_request_is_allowlisted(self) -> None:
        text = (ROOT / "examples" / "request.json").read_text(encoding="utf-8")
        self.assertEqual([], checks.find_safety_markers(text, "examples/request.json"))

    def test_secret_assignment_is_rejected(self) -> None:
        synthetic_assignment = "to" + "ken" + ' = "abcdefghijklmnop"'
        findings = checks.find_safety_markers(synthetic_assignment)
        self.assertTrue(any("SECRET_PATTERN" in finding for finding in findings))


class RepositoryTests(unittest.TestCase):
    def test_all_repository_checks(self) -> None:
        self.assertEqual([], checks.run_checks(ROOT))

    def test_pyproject_is_pinned_and_has_no_application_dependencies(self) -> None:
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('"jsonschema==4.26.0"', text)
        self.assertIn('"ruamel.yaml==0.18.10"', text)
        self.assertNotIn("fastapi", text)
        self.assertNotIn("docker", text)

    def test_examples_remain_parseable_json(self) -> None:
        for path in (ROOT / "examples").glob("*.json"):
            with self.subTest(example=path.name):
                json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
