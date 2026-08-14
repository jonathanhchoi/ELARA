"""Reconcile run artifacts against their denominators, ledgers, and checksums.

Each subcommand takes explicit file arguments so it works whatever _vNNN
version numbers a project is on. Column names may vary; a column is located
by the first header containing the listed needle, case-insensitively.

    corpus --unit-space <csv> --manifest <csv>
        unit-space column: first header containing "unit_id" (fallback "unit")
        manifest columns: same ID rule, plus first header containing "status"
        Checks: unit-space IDs are unique and nonempty; every unit-space ID
        appears exactly once in the manifest; no manifest ID falls outside the
        unit space; every manifest row has a nonempty terminal status; and the
        status counts sum to the unit-space denominator.

    coding --manifest <corpus csv> --ledger <csv>
        Both files use the "unit_id"/"unit" ID rule; the ledger also needs a
        "status" column. Checks: every corpus unit appears in the ledger with
        exactly one nonempty-status row. If the ledger also has columns
        containing "attempted", "succeeded", "failed", and "unusable", each
        fully numeric row must reconcile: attempted = succeeded + failed +
        unusable (a totals row is just another row).

    coverage --observations <jsonl-or-csv> --coverage <csv>
        Observation ID: first header or JSON key containing "observation_id"
        (fallback "observation"); the coverage file also needs a "status"
        column. Checks: every observation ID appears exactly once in the
        coverage file; no coverage row names an unknown observation; and the
        coverage status counts sum to the observation count.

    checksums --manifest <csv> [--root <dir>]
        Same engine and column rules as scripts/verify_freeze.py.

Pass --json to any subcommand for a machine-readable summary on stdout. The
exit status is nonzero on any failure.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

from verify_freeze import find_column, verify_manifest


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def _read_observations(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read a JSONL or CSV observations file as (field names, records)."""

    if path.suffix.lower() != ".jsonl":
        return _read_csv(path)
    records: list[dict[str, str]] = []
    fields: list[str] = []
    with path.open(encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{line_number}: JSONL row is not an object")
            for key in record:
                if key not in fields:
                    fields.append(key)
            records.append({key: str(value) for key, value in record.items()})
    return fields, records


def _cell(record: dict[str, str], column: str) -> str:
    return (record.get(column) or "").strip()


def validate_corpus(unit_space: Path, manifest: Path) -> tuple[list[str], dict[str, object]]:
    errors: list[str] = []
    space_headers, space_rows = _read_csv(unit_space)
    manifest_headers, manifest_rows = _read_csv(manifest)
    space_id = find_column(space_headers, "unit_id", "unit")
    manifest_id = find_column(manifest_headers, "unit_id", "unit")
    status_column = find_column(manifest_headers, "status")
    if space_id is None:
        return [f"{unit_space}: no header containing 'unit_id' or 'unit'"], {}
    if manifest_id is None:
        return [f"{manifest}: no header containing 'unit_id' or 'unit'"], {}
    if status_column is None:
        return [f"{manifest}: no header containing 'status'"], {}

    space_ids = [_cell(row, space_id) for row in space_rows]
    for line_number, unit in enumerate(space_ids, 2):
        if not unit:
            errors.append(f"{unit_space}:{line_number}: empty unit ID")
    for unit, count in sorted(Counter(unit for unit in space_ids if unit).items()):
        if count > 1:
            errors.append(f"{unit_space}: duplicate unit ID {unit!r} ({count} rows)")

    manifest_counts = Counter(_cell(row, manifest_id) for row in manifest_rows)
    denominator = set(unit for unit in space_ids if unit)
    for unit in sorted(denominator):
        if manifest_counts.get(unit, 0) == 0:
            errors.append(f"{manifest}: unit {unit!r} from the unit space is missing")
        elif manifest_counts[unit] > 1:
            errors.append(
                f"{manifest}: unit {unit!r} appears {manifest_counts[unit]} times; expected exactly once"
            )
    for unit in sorted(set(manifest_counts) - denominator):
        errors.append(f"{manifest}: unit {unit!r} is not in the unit space")

    status_counts: Counter[str] = Counter()
    for line_number, row in enumerate(manifest_rows, 2):
        status = _cell(row, status_column)
        if not status:
            errors.append(f"{manifest}:{line_number}: row has no terminal status")
        else:
            status_counts[status] += 1
    if sum(status_counts.values()) != len(denominator):
        errors.append(
            f"status counts sum to {sum(status_counts.values())} but the unit space "
            f"has {len(denominator)} units; the denominator does not reconcile"
        )
    summary = {
        "unit_space_units": len(denominator),
        "manifest_rows": len(manifest_rows),
        "status_counts": dict(sorted(status_counts.items())),
    }
    return errors, summary


def validate_coding(manifest: Path, ledger: Path) -> tuple[list[str], dict[str, object]]:
    errors: list[str] = []
    manifest_headers, manifest_rows = _read_csv(manifest)
    ledger_headers, ledger_rows = _read_csv(ledger)
    manifest_id = find_column(manifest_headers, "unit_id", "unit")
    ledger_id = find_column(ledger_headers, "unit_id", "unit")
    status_column = find_column(ledger_headers, "status")
    if manifest_id is None:
        return [f"{manifest}: no header containing 'unit_id' or 'unit'"], {}
    if ledger_id is None:
        return [f"{ledger}: no header containing 'unit_id' or 'unit'"], {}
    if status_column is None:
        return [f"{ledger}: no header containing 'status'"], {}

    active_rows: Counter[str] = Counter()
    for row in ledger_rows:
        if _cell(row, status_column):
            active_rows[_cell(row, ledger_id)] += 1
    corpus_units = sorted({_cell(row, manifest_id) for row in manifest_rows if _cell(row, manifest_id)})
    for unit in corpus_units:
        if active_rows.get(unit, 0) == 0:
            errors.append(f"{ledger}: corpus unit {unit!r} has no ledger row with a status")
        elif active_rows[unit] > 1:
            errors.append(
                f"{ledger}: corpus unit {unit!r} has {active_rows[unit]} status rows; expected exactly one"
            )

    count_columns = {
        name: find_column(ledger_headers, name)
        for name in ("attempted", "succeeded", "failed", "unusable")
    }
    checked_counts = 0
    if all(count_columns.values()):
        for line_number, row in enumerate(ledger_rows, 2):
            cells = {name: _cell(row, column) for name, column in count_columns.items()}
            if not all(cell.lstrip("-").isdigit() for cell in cells.values()):
                continue
            checked_counts += 1
            values = {name: int(cell) for name, cell in cells.items()}
            expected = values["succeeded"] + values["failed"] + values["unusable"]
            if values["attempted"] != expected:
                errors.append(
                    f"{ledger}:{line_number}: attempted={values['attempted']} but "
                    f"succeeded+failed+unusable={expected}; the ledger does not reconcile"
                )
    summary = {
        "corpus_units": len(corpus_units),
        "ledger_rows": len(ledger_rows),
        "count_rows_checked": checked_counts,
    }
    return errors, summary


def validate_coverage(observations: Path, coverage: Path) -> tuple[list[str], dict[str, object]]:
    errors: list[str] = []
    observation_fields, observation_rows = _read_observations(observations)
    coverage_headers, coverage_rows = _read_csv(coverage)
    observation_id = find_column(observation_fields, "observation_id", "observation")
    coverage_id = find_column(coverage_headers, "observation_id", "observation")
    status_column = find_column(coverage_headers, "status")
    if observation_id is None:
        return [f"{observations}: no field containing 'observation_id' or 'observation'"], {}
    if coverage_id is None:
        return [f"{coverage}: no header containing 'observation_id' or 'observation'"], {}
    if status_column is None:
        return [f"{coverage}: no header containing 'status'"], {}

    observation_ids = [_cell(row, observation_id) for row in observation_rows]
    coverage_counts = Counter(_cell(row, coverage_id) for row in coverage_rows)
    for observation in sorted(set(observation_ids)):
        if coverage_counts.get(observation, 0) == 0:
            errors.append(f"{coverage}: observation {observation!r} is missing")
        elif coverage_counts[observation] > 1:
            errors.append(
                f"{coverage}: observation {observation!r} appears "
                f"{coverage_counts[observation]} times; expected exactly once"
            )
    for observation in sorted(set(coverage_counts) - set(observation_ids)):
        errors.append(f"{coverage}: unknown observation {observation!r}")

    status_counts = Counter(
        _cell(row, status_column) for row in coverage_rows if _cell(row, status_column)
    )
    if sum(status_counts.values()) != len(observation_ids):
        errors.append(
            f"coverage status counts sum to {sum(status_counts.values())} but there are "
            f"{len(observation_ids)} observations; coverage does not reconcile"
        )
    summary = {
        "observations": len(observation_ids),
        "coverage_rows": len(coverage_rows),
        "status_counts": dict(sorted(status_counts.items())),
    }
    return errors, summary


def validate_checksums(manifest: Path, root: Path) -> tuple[list[str], dict[str, object]]:
    rows, errors = verify_manifest(manifest, root)
    if not rows and not errors:
        errors = [f"{manifest}: the manifest has no rows"]
    summary = {
        "files_checked": len(rows),
        "files_passed": sum(1 for _path, verdict in rows if verdict == "PASS"),
    }
    return errors, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    corpus = subparsers.add_parser("corpus", help="reconcile a corpus manifest against the unit space")
    corpus.add_argument("--unit-space", type=Path, required=True)
    corpus.add_argument("--manifest", type=Path, required=True)

    coding = subparsers.add_parser("coding", help="reconcile a coding ledger against the corpus manifest")
    coding.add_argument("--manifest", type=Path, required=True)
    coding.add_argument("--ledger", type=Path, required=True)

    coverage = subparsers.add_parser("coverage", help="reconcile audit coverage against observations")
    coverage.add_argument("--observations", type=Path, required=True)
    coverage.add_argument("--coverage", type=Path, required=True)

    checksums = subparsers.add_parser("checksums", help="recompute a checksum manifest")
    checksums.add_argument("--manifest", type=Path, required=True)
    checksums.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])

    for subparser in (corpus, coding, coverage, checksums):
        subparser.add_argument("--json", action="store_true", help="print a JSON summary to stdout")

    args = parser.parse_args()
    try:
        if args.subcommand == "corpus":
            errors, summary = validate_corpus(args.unit_space.resolve(), args.manifest.resolve())
        elif args.subcommand == "coding":
            errors, summary = validate_coding(args.manifest.resolve(), args.ledger.resolve())
        elif args.subcommand == "coverage":
            errors, summary = validate_coverage(args.observations.resolve(), args.coverage.resolve())
        else:
            errors, summary = validate_checksums(args.manifest.resolve(), args.root.resolve())
    except (OSError, UnicodeDecodeError, ValueError, csv.Error, json.JSONDecodeError) as exc:
        print(f"Could not read the input files: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(
            json.dumps(
                {
                    "subcommand": args.subcommand,
                    "passed": not errors,
                    "errors": errors,
                    "summary": summary,
                },
                indent=2,
            )
        )
    elif errors:
        print(f"Run validation ({args.subcommand}) FAILED:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
    else:
        print(f"Run validation ({args.subcommand}) passed: {summary}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
