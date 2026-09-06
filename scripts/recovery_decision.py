"""Read-only operational recovery decisions shared by routers and host adapters.

This verifies recorded evidence, not the truth or meaning of a researcher's
words. The parent must accurately transcribe and interpret the current user
instruction. Neither a state flag nor this helper grants authority, validates a
scientific result, allocates a retry, launches a process, or clears a stop.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ACTIONS = {"operational_repair", "synthetic_capability", "operational_migration", "resume_dispatch"}
REQUIREMENTS = {
    "operational_repair": (),
    "synthetic_capability": ("independent_review", "offline_boundary_test"),
    "operational_migration": ("independent_review", "offline_boundary_test", "scientific_bindings", "history_preserved"),
    "resume_dispatch": ("independent_review", "offline_boundary_test", "scientific_bindings", "history_preserved",
                        "live_capability", "activation_review", "exclusive_ownership", "attempt_reconciliation"),
}


def read_reference(root: Path, reference: dict) -> bytes:
    if not isinstance(reference, dict) or set(reference) != {"path", "sha256"}:
        raise ValueError("reference must contain path and sha256")
    relative, digest = reference["path"], reference["sha256"]
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise ValueError("reference path must be repository-relative")
    target = (root / relative).resolve()
    if Path(relative).is_absolute() or not target.is_relative_to(root.resolve()):
        raise ValueError("reference escapes root")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("invalid reference digest")
    raw = target.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("reference changed")
    return raw


def _instruction(root: Path, record: dict) -> None:
    if record.get("source_kind") != "researcher_instruction":
        raise ValueError("authority requires a researcher instruction")
    quote = record.get("quote")
    if not isinstance(quote, str) or not quote.strip():
        raise ValueError("authority requires the exact instruction excerpt")
    if quote not in read_reference(root, record["source"]).decode("utf-8-sig"):
        raise ValueError("instruction excerpt not found in bound source")


def decide(root: Path, request: dict) -> dict:
    """Return a closed decision; malformed or changed evidence requires repair.

Required request keys: schema_version, run_id, action, binding_sha256, candidate_sha256,
    authorities, restrictions, evidence. Each authority has id, source_kind,
    source {path,sha256}, quote, run_id, binding_sha256, actions. Restrictions
    have the same bound instruction source plus kind and authority_id (for
    revocation/operation_limit); operation limits include maximum and consumed.
    Evidence maps requirement names to hash-bound JSON receipts with
    requirement, status='passed', run_id, binding_sha256, and candidate_sha256.
    candidate_sha256 identifies the exact operational manifest (code, host,
    configuration, runtime and input inventory); authority remains bound to
    the scientific scope so standing authority survives reviewed repairs. Optional
    external_unavailable is a bound JSON receipt with status='unavailable'.

    Scientific changes and unknown corpus attempt eligibility are restrictions,
    never supplied authority. The caller must include all current restrictions;
    source verification alone cannot discover omitted or misinterpreted policy.
    """
    result = {"schema_version": "1.0", "outcome": "repair", "authority_refs": [],
              "unmet_requirements": [], "reason_codes": [], "state_status": "paused",
              "outstanding_user_inputs": []}

    def finish(outcome, reason, unmet=()):
        result.update(outcome=outcome, reason_codes=[reason], unmet_requirements=list(unmet),
                      state_status="waiting_for_user" if outcome == "request_user" else
                          "ready" if outcome == "proceed" and request.get("action") == "resume_dispatch" else "paused",
                      outstanding_user_inputs=[reason] if outcome == "request_user" else [])
        return result

    try:
        allowed = {"schema_version", "run_id", "action", "binding_sha256", "candidate_sha256", "authorities", "restrictions", "evidence", "external_unavailable"}
        if not isinstance(request, dict) or set(request) - allowed or request.get("schema_version") != "1.0":
            raise ValueError("invalid request contract")
        action, run_id, binding = request["action"], request["run_id"], request["binding_sha256"]
        candidate = request["candidate_sha256"]
        if (action not in ACTIONS or not isinstance(run_id, str) or not run_id
                or not re.fullmatch(r"[0-9a-f]{64}", binding) or not re.fullmatch(r"[0-9a-f]{64}", candidate)):
            raise ValueError("invalid action scope")
        authorities, restrictions, evidence = request["authorities"], request["restrictions"], request["evidence"]
        if not isinstance(authorities, list) or not isinstance(restrictions, list) or not isinstance(evidence, dict):
            raise ValueError("invalid decision inventory")
        active = {}
        for item in authorities:
            _instruction(root, item)
            if not isinstance(item["id"], str) or not item["id"] or item["id"] in active:
                raise ValueError("invalid or duplicate authority identifier")
            if not isinstance(item["actions"], list) or not set(item["actions"]) <= ACTIONS:
                raise ValueError("invalid authority actions")
            active[item["id"]] = item
        material = []
        for item in restrictions:
            kind = item["kind"]
            if kind in {"scientific_change", "unknown_attempt_eligibility"}:
                proof = json.loads(read_reference(root, item["source"]))
                if proof.get("binding_sha256") != binding or proof.get("restriction") != kind:
                    raise ValueError("restriction evidence mismatch")
                material.append(kind)
                continue
            _instruction(root, item)
            if kind == "revocation":
                active.pop(item["authority_id"], None)
            elif kind == "operation_limit":
                maximum, consumed = item["maximum"], item["consumed"]
                if type(maximum) is not int or type(consumed) is not int or min(maximum, consumed) < 0:
                    raise ValueError("invalid operation accounting")
                if consumed >= maximum:
                    active.pop(item["authority_id"], None)
            elif kind == "researcher_pause":
                material.append(kind)
            else:
                raise ValueError("unknown restriction")
        applicable = [item for item in active.values() if item["run_id"] == run_id
                      and item["binding_sha256"] == binding and action in item["actions"]]
        result["authority_refs"] = [{"id": item["id"], "source": item["source"]} for item in applicable]
        if material:
            return finish("request_user", material[0], material)
        if not applicable:
            return finish("request_user", "missing_scoped_authority")
        missing = []
        for requirement in REQUIREMENTS[action]:
            if requirement not in evidence:
                missing.append(requirement)
                continue
            proof = json.loads(read_reference(root, evidence[requirement]))
            if (proof.get("requirement") != requirement or proof.get("status") != "passed"
                    or proof.get("binding_sha256") != binding or proof.get("run_id") != run_id
                    or proof.get("candidate_sha256") != candidate):
                missing.append(requirement)
        if "external_unavailable" in request:
            proof = json.loads(read_reference(root, request["external_unavailable"]))
            if (proof.get("status") != "unavailable" or proof.get("binding_sha256") != binding
                    or proof.get("run_id") != run_id or proof.get("candidate_sha256") != candidate):
                raise ValueError("external capability evidence mismatch")
            return finish("wait_external", "external_capability_unavailable", missing)
        if missing:
            return finish("repair", "verification_incomplete", missing)
        return finish("proceed", "scoped_authority_and_evidence_verified")
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return finish("repair", "invalid_or_changed_decision_evidence", ["reconcile_decision_evidence"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args()
    try:
        request = json.loads(args.request.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        request = {}
    result = decide(args.root, request)
    print(json.dumps(result, indent=2, sort_keys=True))
    return {"proceed": 0, "repair": 2, "wait_external": 3, "request_user": 4}[result["outcome"]]


if __name__ == "__main__":
    raise SystemExit(main())
