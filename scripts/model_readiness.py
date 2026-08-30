"""Offline assessment of the installing agent's live model-access evidence.

The host agent retrieves current official guidance and inspects its own session;
this helper validates that evidence and produces a nonblocking advisory. It does
not discover models, read credentials, launch agents, change settings, or make
network/model calls. No model names or model rankings are built into the kit.
See workflow/shared/model-readiness.md for the evidence collection contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit


PLATFORMS = ("codex", "claude")
HOST_NAMES = {"codex": "Codex", "claude": "Claude Code"}
OFFICIAL_DOMAINS = {
    "codex": {"developers.openai.com", "platform.openai.com", "learn.chatgpt.com", "help.openai.com", "openai.com"},
    "claude": {"code.claude.com", "platform.claude.com", "support.claude.com", "claude.com", "www.anthropic.com", "anthropic.com"},
}
PLAN_ADVICE = {
    "codex": "For large-scale research, ELARA strongly recommends ChatGPT Pro 20x or the current highest-volume equivalent.",
    "claude": "For large-scale research, ELARA strongly recommends Claude Max 20x or the current highest-volume equivalent.",
}
CAPACITY_CAVEAT = (
    "Check current plan terms: higher capacity is not unlimited usage or a guarantee "
    "that every frontier model is included; additional credits may be required. "
    "Subscription access and API billing are separate."
)
MAX_EVIDENCE_BYTES = 64 * 1024
# A cached check never establishes current access indefinitely. Every install or
# update still requires a fresh check, even within this maximum age.
MAX_EVIDENCE_AGE = timedelta(hours=24)
CLOCK_SKEW = timedelta(minutes=5)
NATIVE_EVIDENCE = {"active_session", "account_model_catalog", "host_access_status"}
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._:/()+-]{0,119}\Z")
SECRET = re.compile(r"(?i)(?:\bsk-|\bbearer\s|\b(?:api[_ -]?key|access[_ -]?token|password)\s*[:=])")


class EvidenceError(ValueError):
    """Messages are fixed diagnostics, never excerpts from potentially private input."""


def _object(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise EvidenceError("Evidence has missing or unexpected fields.")


def _choice(value, choices):
    if not isinstance(value, str) or value not in choices:
        raise EvidenceError("Evidence contains an unsupported status.")


def _text(value, *, identifier=False, nullable=False):
    if nullable and value is None:
        return
    if not isinstance(value, str) or not value.strip() or len(value) > 2000:
        raise EvidenceError("Evidence contains an empty, invalid, or oversized text field.")
    if SECRET.search(value) or any(ord(c) < 32 for c in value):
        raise EvidenceError("Evidence contains unsafe text; supply only secret-free summaries.")
    if identifier and not IDENTIFIER.fullmatch(value):
        raise EvidenceError("Evidence contains an invalid model or effort identifier.")


def _timestamp(value, now):
    if not isinstance(value, str):
        raise EvidenceError("Evidence needs timezone-aware timestamps.")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("Evidence needs timezone-aware timestamps.") from exc
    if stamp.tzinfo is None:
        raise EvidenceError("Evidence needs timezone-aware timestamps.")
    if now - stamp > MAX_EVIDENCE_AGE:
        raise EvidenceError("Evidence is stale; repeat the live check.")
    if stamp - now > CLOCK_SKEW:
        raise EvidenceError("Evidence is future-dated; check the timestamp.")
    return stamp


def _source(source, platform, now):
    _object(source, ("url", "retrieved_at", "finding"))
    _text(source["url"])
    _text(source["finding"])
    try:
        url = urlsplit(source["url"])
        valid = (
            url.scheme == "https" and url.hostname in OFFICIAL_DOMAINS[platform]
            and not url.username and not url.password and not url.query
            and url.port in (None, 443)
        )
    except ValueError:
        valid = False
    if not valid:
        raise EvidenceError("Recommendation sources must be canonical HTTPS pages from the applicable provider.")
    _timestamp(source["retrieved_at"], now)


def evidence_template(platforms, now=None):
    """An explicitly unverified scaffold; the agent fills it from actual observations."""
    stamp = (now or datetime.now(timezone.utc)).isoformat()
    return {
        "schema_version": "1.0",
        "platforms": {platform: {
            "checked_at": stamp,
            "host_surface": HOST_NAMES[platform] + " (identify the actual app or CLI)",
            "recommended_model": None,
            "recommended_effort": None,
            "effort_policy": "unknown",
            "sources": [],
            "current_model": None,
            "current_effort": None,
            "selection_kind": "unknown",
            "access": {
                "status": "unknown", "kind": "unknown", "model": None,
                "observed_at": stamp, "detail": "Not inspected yet.",
            },
        } for platform in platforms},
    }


def _validate_record(record, platform, now):
    _object(record, (
        "checked_at", "host_surface", "recommended_model", "recommended_effort",
        "effort_policy", "sources", "current_model", "current_effort", "selection_kind", "access",
    ))
    _timestamp(record["checked_at"], now)
    _text(record["host_surface"])
    for key in ("recommended_model", "recommended_effort", "current_model", "current_effort"):
        _text(record[key], identifier=True, nullable=True)
    _choice(record["effort_policy"], ("resolved", "not_supported", "unknown"))
    _choice(record["selection_kind"], ("active_session", "configuration", "user_report", "unknown"))
    if (record["effort_policy"] == "resolved") != (record["recommended_effort"] is not None):
        raise EvidenceError("The recommended effort and effort-policy status disagree.")
    sources = record["sources"]
    if not isinstance(sources, list) or len(sources) > 8:
        raise EvidenceError("Evidence needs a bounded list of official sources.")
    for source in sources:
        _source(source, platform, now)
    if record["recommended_model"] is not None and not sources:
        raise EvidenceError("A strongest-model recommendation needs current official source evidence.")
    access = record["access"]
    _object(access, ("status", "kind", "model", "observed_at", "detail"))
    _choice(access["status"], ("available", "unavailable", "unknown"))
    _choice(access["kind"], NATIVE_EVIDENCE | {"user_report", "configuration", "catalog_only", "unknown"})
    _text(access["model"], identifier=True, nullable=True)
    _text(access["detail"])
    _timestamp(access["observed_at"], now)
    if access["kind"] == "active_session" and (
        access["status"] != "available" or access["model"] != record["current_model"]
        or record["selection_kind"] != "active_session"
    ):
        raise EvidenceError("Active-session evidence must identify the model actually running.")
    if access["status"] == "unavailable" and access["model"] and access["model"] == record["current_model"]:
        raise EvidenceError("Access denial conflicts with the reported running model; repeat the check.")


def assess(platform, record=None, *, now=None, diagnostic=None):
    """Unknown/incomplete evidence warns; it never fails software installation."""
    now = now or datetime.now(timezone.utc)
    report = {
        "platform": platform, "status": "unverified", "access_status": "unknown",
        "selection_status": "unknown", "recommended_model": None,
        "recommended_effort": None, "current_model": None, "current_effort": None,
        "checked_at": None, "basis": "no_evidence", "source_urls": [],
        "warnings": [], "recommendations": [PLAN_ADVICE[platform], CAPACITY_CAVEAT],
    }
    if record is not None:
        try:
            _validate_record(record, platform, now)
        except EvidenceError as exc:
            diagnostic = str(exc)
            record = None
    if record is not None:
        for key in ("recommended_model", "recommended_effort", "current_model", "current_effort", "checked_at"):
            report[key] = record[key]
        report["basis"] = "agent_collected_evidence"
        report["source_urls"] = [source["url"] for source in record["sources"]]
        access = record["access"]
        target = record["recommended_model"]
        if target and access["model"] == target and access["kind"] in NATIVE_EVIDENCE:
            report["access_status"] = access["status"]
        if target and record["current_model"] and record["selection_kind"] == "active_session":
            if record["current_model"] != target:
                report["selection_status"] = "different_model"
            elif record["effort_policy"] == "not_supported":
                report["selection_status"] = "recommended"
            elif record["effort_policy"] == "resolved" and record["current_effort"]:
                report["selection_status"] = (
                    "recommended" if record["current_effort"] == record["recommended_effort"]
                    else "different_effort"
                )
    access_status = report["access_status"]
    selection = report["selection_status"]
    host = HOST_NAMES[platform]
    if access_status == "unavailable":
        report["status"] = "upgrade_recommended"
        report["warnings"].append(
            host + ": the current strongest model (" + report["recommended_model"]
            + ") is unavailable on this route. ELARA strongly recommends upgrading "
            "your plan or obtaining the required account/organization access before "
            "substantial research. An app update may also be needed."
        )
    elif access_status == "unknown":
        report["warnings"].append(
            host + ": access to the current strongest model could not be verified. "
            "This is not proof that access is missing. ELARA strongly recommends "
            "verifying access and, if necessary, upgrading before substantial research."
        )
    elif selection == "recommended":
        report["status"] = "recommended"
    else:
        report["status"] = "selection_recommended"
    if selection in ("different_model", "different_effort") and access_status != "unavailable":
        report["warnings"].append(
            host + ": ELARA strongly recommends selecting " + report["recommended_model"]
            + (" with " + report["recommended_effort"] + " reasoning" if report["recommended_effort"] else "")
            + ". The current selection differs; this alone does not call for a subscription upgrade. "
            "Do not change an approved research model or settings without the researcher's decision."
        )
    elif access_status == "available" and selection == "unknown":
        report["warnings"].append(
            host + ": model access is confirmed by the supplied evidence, but the active "
            "model/reasoning configuration is not fully verified. Inspect it before substantial research."
        )
    if diagnostic:
        report["warnings"].append(diagnostic)
    return report


def _load_evidence(path):
    try:
        with Path(path).open("rb") as stream:
            raw = stream.read(MAX_EVIDENCE_BYTES + 1)
        if len(raw) > MAX_EVIDENCE_BYTES:
            raise EvidenceError("Evidence file exceeds the size limit.")
        def unique_keys(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise EvidenceError("Evidence contains duplicate JSON keys.")
                result[key] = value
            return result
        evidence = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_keys)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        # Never echo the path, file contents, or parser error (which may contain secrets).
        raise EvidenceError("Evidence file is unreadable, oversized, or invalid JSON.") from exc
    _object(evidence, ("schema_version", "platforms"))
    if evidence["schema_version"] != "1.0" or not isinstance(evidence["platforms"], dict):
        raise EvidenceError("Evidence has an unsupported schema.")
    if set(evidence["platforms"]) - set(PLATFORMS):
        raise EvidenceError("Evidence names an unsupported platform.")
    return evidence["platforms"], hashlib.sha256(raw).hexdigest()


def build_advisory(platforms, evidence_path=None, *, now=None):
    platforms = list(dict.fromkeys(platforms))
    if any(platform not in PLATFORMS for platform in platforms):
        raise ValueError("Unsupported platform")
    records, digest, diagnostic = {}, None, None
    if evidence_path and platforms:
        try:
            records, digest = _load_evidence(evidence_path)
        except EvidenceError as exc:
            diagnostic = str(exc)
    reports = {
        platform: assess(platform, records.get(platform), now=now, diagnostic=diagnostic)
        for platform in platforms
    }
    return {
        "schema_version": "1.0", "advisory_only": True,
        "status": "assessed" if platforms else "not_checked",
        "evidence_sha256": digest, "platforms": reports,
        "warnings": [warning for report in reports.values() for warning in report["warnings"]],
        "recommendations": list(dict.fromkeys(
            item for report in reports.values() for item in report["recommendations"]
        )),
        "network_calls": 0, "model_calls": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--platform", choices=(*PLATFORMS, "all", "none"), required=True)
    parser.add_argument("--evidence", type=Path, help="secret-free evidence collected for this host session")
    parser.add_argument("--template", action="store_true", help="print an unverified evidence scaffold")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    platforms = list(PLATFORMS) if args.platform == "all" else ([] if args.platform == "none" else [args.platform])
    if args.template:
        print(json.dumps(evidence_template(platforms), indent=2))
        return 0
    report = build_advisory(platforms, args.evidence)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for platform, result in report["platforms"].items():
            print("MODEL CHECK: " + HOST_NAMES[platform] + " - " + result["status"])
        for warning in report["warnings"]:
            print("WARNING: " + warning)
        for recommendation in report["recommendations"]:
            print("RECOMMENDATION: " + recommendation)
        print("Advisory only: installation may continue; no settings or subscriptions were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
