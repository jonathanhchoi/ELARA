"""Public synthetic recovery transitions; no provider calls or research data."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from recovery_decision import ACTIONS, REQUIREMENTS, decide
from validate_workflow import validate_state


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.binding = "a" * 64
        self.candidate = "b" * 64
        self.quote = "I authorize operational repairs, synthetic tests, reviewed migration, and resumption under the frozen rules."
        source = self.write("instruction.md", self.quote)
        self.authority = {"id": "user-1", "source_kind": "researcher_instruction", "source": source,
                          "quote": self.quote, "run_id": "public-run", "binding_sha256": self.binding,
                          "actions": sorted(ACTIONS)}
        self.request = {"schema_version": "1.0", "run_id": "public-run", "action": "resume_dispatch",
                        "binding_sha256": self.binding, "candidate_sha256": self.candidate,
                        "authorities": [self.authority], "restrictions": [], "evidence": {}}

    def write(self, name, value):
        raw = (json.dumps(value, sort_keys=True) if not isinstance(value, str) else value).encode()
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return {"path": name, "sha256": hashlib.sha256(raw).hexdigest()}

    def proof(self, requirement, **changes):
        proof = {"requirement": requirement, "status": "passed", "run_id": "public-run",
                 "binding_sha256": self.binding, "candidate_sha256": self.candidate}
        proof.update(changes)
        self.request["evidence"][requirement] = self.write(requirement + ".json", proof)

    def complete_proofs(self):
        for name in REQUIREMENTS["resume_dispatch"]:
            self.proof(name)

    def restrict(self, kind, **fields):
        quote = "Only one more synthetic operation is permitted." if kind == "operation_limit" else "Stop the previously authorized work."
        self.request["restrictions"].append({"kind": kind, "source_kind": "researcher_instruction",
            "source": self.write(kind + ".md", quote), "quote": quote, "authority_id": "user-1", **fields})

    def test_covered_failure_repair_and_resume_without_another_approval(self):
        outcomes = [decide(self.root, self.request)]
        self.request["action"] = "operational_repair"
        outcomes.append(decide(self.root, self.request))
        self.request["action"] = "synthetic_capability"
        outcomes.append(decide(self.root, self.request))
        self.proof("offline_boundary_test")
        self.proof("independent_review")
        outcomes.append(decide(self.root, self.request))
        self.request["action"] = "resume_dispatch"
        outcomes.append(decide(self.root, self.request))
        self.complete_proofs()
        outcomes.append(decide(self.root, self.request))
        self.assertEqual([item["outcome"] for item in outcomes], ["repair", "proceed", "repair", "proceed", "repair", "proceed"])
        self.assertTrue(all(not item["outstanding_user_inputs"] for item in outcomes))

    def test_configuration_text_is_not_live_capability(self):
        self.complete_proofs()
        self.request["evidence"]["live_capability"] = self.write("config.json", {"hooks_enabled": True, "model": "synthetic"})
        result = decide(self.root, self.request)
        self.assertEqual(result["outcome"], "repair")
        self.assertEqual(result["unmet_requirements"], ["live_capability"])

    def test_authorized_repair_never_marks_research_dispatch_ready(self):
        self.complete_proofs()
        for action in ("operational_repair", "synthetic_capability", "operational_migration"):
            with self.subTest(action=action):
                self.request["action"] = action
                result = decide(self.root, self.request)
                self.assertEqual(result["outcome"], "proceed")
                self.assertEqual(result["state_status"], "paused")
                anchor = {"request": self.write("request.json", self.request),
                          "result": self.write("result.json", result)}
                self.write_state(status="paused", recovery_decision=anchor)
                self.assertEqual(validate_state(self.root), [])
                for status in ("ready", "running"):
                    self.write_state(status=status, recovery_decision=anchor)
                    self.assertTrue(validate_state(self.root))

    def test_stale_candidate_or_other_run_evidence_cannot_authorize_resume(self):
        self.complete_proofs()
        for changes in ({"candidate_sha256": "c" * 64}, {"run_id": "other-run"}, {"binding_sha256": "d" * 64}):
            with self.subTest(changes=changes):
                self.proof("live_capability", **changes)
                self.assertEqual(decide(self.root, self.request)["unmet_requirements"], ["live_capability"])

    def test_changed_proof_and_false_instruction_quote_require_investigation(self):
        self.complete_proofs()
        (self.root / "live_capability.json").write_text("{}")
        self.assertEqual(decide(self.root, self.request)["outcome"], "repair")
        self.complete_proofs()
        self.authority["quote"] = "Not in the actual user instruction"
        self.assertEqual(decide(self.root, self.request)["reason_codes"], ["invalid_or_changed_decision_evidence"])

    def test_arbitrary_authority_boolean_does_not_grant_permission(self):
        self.complete_proofs()
        self.request["authorities"] = []
        self.assertEqual(decide(self.root, self.request)["outcome"], "request_user")
        self.request["authorized"] = True
        self.assertEqual(decide(self.root, self.request)["outcome"], "repair")

    def test_cli_interrupted_or_missing_request_returns_closed_repair(self):
        script = Path(__file__).resolve().parents[1] / "scripts/recovery_decision.py"
        for name, content in (("missing.json", None), ("partial.json", '{"schema_')):
            with self.subTest(name=name):
                path = self.root / name
                if content is not None:
                    path.write_text(content, encoding="utf-8")
                result = subprocess.run([sys.executable, "-B", str(script), "--root", str(self.root),
                                         "--request", str(path)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stderr, "")
                self.assertEqual(json.loads(result.stdout)["outcome"], "repair")

    def test_explicit_limit_revocation_pause_and_scientific_restrictions_remain(self):
        self.complete_proofs()
        for kind, fields in (("operation_limit", {"maximum": 1, "consumed": 1}), ("revocation", {}), ("researcher_pause", {})):
            with self.subTest(kind=kind):
                self.request["restrictions"] = []
                self.restrict(kind, **fields)
                self.assertEqual(decide(self.root, self.request)["outcome"], "request_user")
        for kind in ("scientific_change", "unknown_attempt_eligibility"):
            self.request["restrictions"] = [{"kind": kind, "source": self.write(kind + ".json", {
                "restriction": kind, "binding_sha256": self.binding})}]
            self.assertEqual(decide(self.root, self.request)["reason_codes"], [kind])

    def test_external_capability_is_a_verified_wait_not_permission(self):
        self.request["external_unavailable"] = self.write("outage.json", {
            "status": "unavailable", "run_id": "public-run", "binding_sha256": self.binding,
            "candidate_sha256": self.candidate})
        result = decide(self.root, self.request)
        self.assertEqual(result["outcome"], "wait_external")
        self.assertFalse(result["outstanding_user_inputs"])

    def write_state(self, **changes):
        state = {"schema_version": "1.5", "workflow_version": "2.8.0", "project_slug": "public",
                 "usage": "tools", "current_stage": "11-scale-up", "status": "paused",
                 "active_artifacts": {}, "approvals": {}, "outstanding_user_inputs": [],
                 "last_run_id": "public-run", "updated_at": "2026-09-06T00:00:00Z"}
        state.update(changes)
        self.write("project/PROJECT_STATE.md", "---\n" + "\n".join(key + ": " + json.dumps(value) for key, value in state.items()) + "\n---\n# Public state\n")

    def test_current_decision_resolves_stale_wait_and_recomputed_state_rejects_staleness(self):
        self.complete_proofs()
        result = decide(self.root, self.request)
        anchor = {"request": self.write("request.json", self.request), "result": self.write("result.json", result)}
        self.write_state(status="waiting_for_user", outstanding_user_inputs=["Please approve recovery"], recovery_decision=anchor)
        self.assertTrue(any("recovery decision contradicts" in error for error in validate_state(self.root)))
        self.write_state(status="ready", recovery_decision=anchor)
        self.assertEqual(validate_state(self.root), [])
        self.proof("live_capability", candidate_sha256="c" * 64)
        self.assertTrue(validate_state(self.root))

    def test_state_rejects_contradictory_inputs_and_checkpoint_alias(self):
        self.write_state(status="ready", outstanding_user_inputs=["unresolved"])
        self.assertTrue(validate_state(self.root))
        self.write_state(status="waiting_for_user")
        self.assertTrue(validate_state(self.root))
        self.write_state(active_artifacts={"run_checkpoint": {"path": "old.json", "sha256": "a" * 64}})
        self.assertTrue(any("contradicts the routing checkpoint" in error for error in validate_state(self.root)))


if __name__ == "__main__":
    unittest.main()
