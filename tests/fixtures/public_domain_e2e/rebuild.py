#!/usr/bin/env python3
"""Rebuild the deterministic public-domain fixture with the Python standard library."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent
INPUTS = BASE / "inputs"
EXPECTED = BASE / "expected" / "reported_numbers.json"


def fail(message: str) -> None:
    raise RuntimeError(message)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            fail(f"{path.name}:{number} is not an object")
        rows.append(value)
    return rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bool_cell(value: str, *, location: str) -> bool:
    lowered = value.strip().lower()
    if lowered not in {"true", "false"}:
        fail(f"{location} must be true or false")
    return lowered == "true"


def keyed(rows: list[dict[str, Any]], *, label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        unit_id = row.get("unit_id")
        if not isinstance(unit_id, str) or not unit_id:
            fail(f"{label} has a missing unit_id")
        if unit_id in result:
            fail(f"{label} has duplicate unit_id {unit_id}")
        result[unit_id] = row
    return result


def validate_record(
    row: dict[str, Any], schema: dict[str, Any], source_text: str
) -> tuple[bool, bool]:
    required = set(schema["required"])
    properties = schema["properties"]
    keys = set(row)
    schema_ok = keys == required and keys <= set(properties)
    schema_ok = schema_ok and isinstance(row.get("unit_id"), str)
    schema_ok = schema_ok and type(row.get("federal_assignment")) is bool
    schema_ok = schema_ok and row.get("institution") in properties["institution"]["enum"]
    schema_ok = schema_ok and isinstance(row.get("exact_quote"), str) and bool(
        row.get("exact_quote")
    )
    schema_ok = schema_ok and row.get("status") in properties["status"]["enum"]
    quote_ok = isinstance(row.get("exact_quote"), str) and row["exact_quote"] in source_text
    return schema_ok, quote_ok


def ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        fail("unexpected zero denominator")
    return round(numerator / denominator, 6)


def binary_metrics(
    predicted: dict[str, bool], actual: dict[str, bool]
) -> dict[str, int | float]:
    if set(predicted) != set(actual):
        fail("validation identifiers do not reconcile")
    tp = sum(predicted[key] and actual[key] for key in actual)
    tn = sum((not predicted[key]) and (not actual[key]) for key in actual)
    fp = sum(predicted[key] and (not actual[key]) for key in actual)
    fn = sum((not predicted[key]) and actual[key] for key in actual)
    precision = ratio(tp, tp + fp)
    recall = ratio(tp, tp + fn)
    return {
        "n": len(actual),
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "accuracy": ratio(tp + tn, len(actual)),
        "precision": precision,
        "recall": recall,
        "f1": round(2 * precision * recall / (precision + recall), 6),
    }


def period_difference(
    records: dict[str, dict[str, Any]], manifest: dict[str, dict[str, Any]]
) -> tuple[float, float, float]:
    early = [
        bool(records[key]["federal_assignment"])
        for key in manifest
        if manifest[key]["period"] == "early"
    ]
    later = [
        bool(records[key]["federal_assignment"])
        for key in manifest
        if manifest[key]["period"] == "later"
    ]
    early_share = ratio(sum(early), len(early))
    later_share = ratio(sum(later), len(later))
    return early_share, later_share, round(early_share - later_share, 6)


def acquire_corpus() -> tuple[list[dict[str, Any]], dict[str, str]]:
    rows = read_csv(INPUTS / "corpus_manifest.csv")
    if [int(row["ordinal"]) for row in rows] != list(range(1, len(rows) + 1)):
        fail("manifest ordinals are not contiguous")
    manifest = keyed(rows, label="corpus manifest")
    texts: dict[str, str] = {}
    acquired: list[dict[str, Any]] = []
    for unit_id, row in manifest.items():
        if not bool_cell(row["public_domain"], location=f"manifest {unit_id} public_domain"):
            fail(f"fixture source {unit_id} is not marked public domain")
        path = INPUTS / row["file"]
        if not path.is_file() or not path.resolve().is_relative_to(INPUTS.resolve()):
            fail(f"missing or unsafe corpus path for {unit_id}")
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            fail(f"empty corpus file for {unit_id}")
        texts[unit_id] = text
        acquired.append(
            {
                **row,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    return acquired, texts


def copy_replication_inputs(package: Path) -> None:
    package.mkdir(parents=True)
    shutil.copytree(INPUTS, package / "inputs")
    shutil.copytree(BASE / "expected", package / "expected")
    shutil.copy2(BASE / "rebuild.py", package / "rebuild.py")
    (package / "README.md").write_text(
        "# Fixture replication package\n\n"
        "Run `python rebuild.py --output rebuild_out` from this directory. "
        "No network access or third-party package is required. The command fails if "
        "any reproduced number differs from `expected/reported_numbers.json`.\n",
        encoding="utf-8",
    )


def package_manifest(package: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in sorted(item for item in package.rglob("*") if item.is_file()):
        result.append(
            {
                "path": path.relative_to(package).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    return result


def rebuild(output: Path) -> dict[str, Any]:
    if output.exists():
        fail(f"output already exists: {output}")
    output.mkdir(parents=True)

    schema = json.loads((INPUTS / "schema.json").read_text(encoding="utf-8"))
    acquired, texts = acquire_corpus()
    manifest = keyed(acquired, label="acquired manifest")
    expected_ids = set(manifest)

    model_a_rows = read_jsonl(INPUTS / "model_a.jsonl")
    model_b_rows = read_jsonl(INPUTS / "model_b.jsonl")
    model_a = keyed(model_a_rows, label="model A")
    model_b = keyed(model_b_rows, label="model B")
    if set(model_a) != expected_ids or set(model_b) != expected_ids:
        fail("model-output identifiers do not reconcile to the corpus")

    checks: dict[str, dict[str, bool]] = {}
    for unit_id in manifest:
        schema_ok, quote_ok = validate_record(model_a[unit_id], schema, texts[unit_id])
        checks[unit_id] = {"schema_ok": schema_ok, "quote_ok": quote_ok}
    if not all(value["schema_ok"] and value["quote_ok"] for value in checks.values()):
        fail("model A schema or exact-quote verification failed")

    b_checks: dict[str, dict[str, bool]] = {}
    for unit_id in manifest:
        schema_ok, quote_ok = validate_record(model_b[unit_id], schema, texts[unit_id])
        b_checks[unit_id] = {"schema_ok": schema_ok, "quote_ok": quote_ok}
    if not all(value["schema_ok"] and value["quote_ok"] for value in b_checks.values()):
        fail("model B schema or exact-quote verification failed")

    pilot_ids = [
        unit_id
        for unit_id, row in manifest.items()
        if bool_cell(row["pilot"], location=f"manifest {unit_id} pilot")
    ]
    pilot_human_rows = read_csv(INPUTS / "pilot_human_codes.csv")
    pilot_human = {
        row["unit_id"]: bool_cell(
            row["federal_assignment"], location=f"pilot code {row['unit_id']}"
        )
        for row in pilot_human_rows
    }
    if set(pilot_human) != set(pilot_ids):
        fail("pilot human-code identifiers do not reconcile")
    pilot_agreement = sum(
        bool(model_a[unit_id]["federal_assignment"]) == pilot_human[unit_id]
        for unit_id in pilot_ids
    )
    pilot_report = {
        "n": len(pilot_ids),
        "schema_pass": sum(checks[key]["schema_ok"] for key in pilot_ids),
        "quote_pass": sum(checks[key]["quote_ok"] for key in pilot_ids),
        "human_agreement_count": pilot_agreement,
        "human_agreement_rate": ratio(pilot_agreement, len(pilot_ids)),
    }

    corpus_report = {
        "manifest_units": len(acquired),
        "unique_units": len(manifest),
        "files_present": len(texts),
        "public_domain_units": sum(
            bool_cell(row["public_domain"], location=f"manifest {key} public_domain")
            for key, row in manifest.items()
        ),
        "gap_count": 0,
    }
    scale_report = {
        "attempted": len(manifest),
        "succeeded": len(model_a),
        "failed": 0,
        "unusable": 0,
        "outstanding": len(manifest) - len(model_a),
        "schema_pass": sum(value["schema_ok"] for value in checks.values()),
        "quote_pass": sum(value["quote_ok"] for value in checks.values()),
    }
    support_report = {
        "audited": len(model_a),
        "supported": sum(
            checks[key]["quote_ok"] and model_a[key]["status"] == "coded" for key in model_a
        ),
        "unsupported": sum(
            not (checks[key]["quote_ok"] and model_a[key]["status"] == "coded")
            for key in model_a
        ),
    }

    human_rows = read_csv(INPUTS / "human_codes.csv")
    human = {
        row["unit_id"]: bool_cell(
            row["federal_assignment"], location=f"human code {row['unit_id']}"
        )
        for row in human_rows
    }
    if not set(human) <= expected_ids or len(human) != len(human_rows):
        fail("held-out human-code identifiers do not reconcile")
    predicted = {key: bool(model_a[key]["federal_assignment"]) for key in human}
    validation = binary_metrics(predicted, human)

    early_share, later_share, difference = period_difference(model_a, manifest)
    positives = sum(bool(row["federal_assignment"]) for row in model_a.values())
    sensitivity = validation["recall"]
    specificity = ratio(
        int(validation["true_negative"]),
        int(validation["true_negative"]) + int(validation["false_positive"]),
    )
    correction_denominator = float(sensitivity) + specificity - 1
    if correction_denominator <= 0:
        fail("validation metrics do not identify a correction")
    observed_share = ratio(positives, len(model_a))
    corrected_share = round((observed_share + specificity - 1) / correction_denominator, 6)
    analysis = {
        "n": len(model_a),
        "positive": positives,
        "negative": len(model_a) - positives,
        "observed_share": observed_share,
        "early_share": early_share,
        "later_share": later_share,
        "early_later_difference": difference,
        "corrected_share": corrected_share,
    }

    agreements = sum(
        model_a[key]["federal_assignment"] == model_b[key]["federal_assignment"]
        for key in manifest
    )
    b_positives = sum(bool(row["federal_assignment"]) for row in model_b.values())
    _, _, b_difference = period_difference(model_b, manifest)
    robustness = {
        "n": len(manifest),
        "agreement_count": agreements,
        "disagreement_count": len(manifest) - agreements,
        "agreement_rate": ratio(agreements, len(manifest)),
        "model_b_positive": b_positives,
        "model_b_share": ratio(b_positives, len(manifest)),
        "absolute_share_difference": round(
            abs(ratio(b_positives, len(manifest)) - observed_share), 6
        ),
        "model_b_early_later_difference": b_difference,
        "absolute_coefficient_difference": round(abs(b_difference - difference), 6),
    }

    report = {
        "pilot": pilot_report,
        "corpus_acquisition": corpus_report,
        "scale_up": scale_report,
        "interpretive_verification": support_report,
        "human_validation": validation,
        "analysis": analysis,
        "robustness": robustness,
    }

    write_jsonl(output / "08-pilot" / "normalized_outputs.jsonl", [model_a[key] for key in pilot_ids])
    write_json(output / "08-pilot" / "pilot_report.json", pilot_report)
    write_json(output / "10-corpus-acquisition" / "corpus_manifest.json", acquired)
    write_json(output / "10-corpus-acquisition" / "integrity_checks.json", corpus_report)
    write_jsonl(output / "11-scale-up" / "raw_model_outputs.jsonl", model_a_rows)
    write_json(output / "11-scale-up" / "schema_quote_checks.json", checks)
    write_json(output / "11-scale-up" / "run_reconciliation.json", scale_report)
    write_json(output / "12-interpretive-verification" / "support_audit.json", support_report)
    write_json(output / "13-human-validation" / "metrics.json", validation)
    write_json(output / "14-analysis-and-correction" / "results.json", analysis)
    write_jsonl(output / "15-robustness" / "raw_model_outputs.jsonl", model_b_rows)
    write_json(output / "15-robustness" / "schema_quote_checks.json", b_checks)
    write_json(output / "15-robustness" / "results.json", robustness)
    write_json(output / "16-replication-package" / "reported_numbers.json", report)

    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    if report != expected:
        fail("rebuilt reported numbers differ from the recorded expectation")

    package = output / "16-replication-package" / "package"
    copy_replication_inputs(package)
    manifest_rows = package_manifest(package)
    write_json(output / "16-replication-package" / "replication_manifest.json", manifest_rows)
    write_json(
        output / "16-replication-package" / "rebuild_verification.json",
        {"matches_expected": True, "network_required": False},
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rebuild(args.output.resolve())


if __name__ == "__main__":
    main()
