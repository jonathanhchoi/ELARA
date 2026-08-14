"""Mechanically verify a freeze manifest by recomputing every file's checksum.

Usage:

    python scripts/verify_freeze.py --manifest project/artifacts/frozen_artifact_manifest_v001.csv

The manifest is a CSV whose header names may vary between projects. The path
column is the first header containing "path", the hash column is the first
header containing "sha256" (falling back to the first containing "hash"), and
the optional size column is the first header containing "byte". Each row's
path is resolved against the kit root (--root, defaulting to this kit), its
SHA-256 and byte size are recomputed, and a per-row pass/fail table is
printed. The exit status is nonzero if any file is missing or does not match.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path


def find_column(headers: list[str], *needles: str) -> str | None:
    """Return the first header containing any needle, trying needles in order."""

    for needle in needles:
        for header in headers:
            if needle in header.lower():
                return header
    return None


def verify_manifest(manifest: Path, root: Path) -> tuple[list[tuple[str, str]], list[str]]:
    """Recompute checksums for every manifest row.

    Returns (rows, errors) where rows are (path, verdict) pairs for the
    per-row table and errors describe every missing or mismatched file.
    """

    errors: list[str] = []
    rows: list[tuple[str, str]] = []
    with manifest.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        path_column = find_column(headers, "path")
        hash_column = find_column(headers, "sha256", "hash")
        size_column = find_column(headers, "byte")
        if path_column is None or hash_column is None:
            return rows, [
                f"{manifest}: could not find the manifest columns; expected a header "
                'containing "path" and one containing "sha256" or "hash", '
                f"found: {', '.join(headers) or '(no header row)'}"
            ]
        for line_number, record in enumerate(reader, 2):
            relative = (record.get(path_column) or "").strip()
            expected_hash = (record.get(hash_column) or "").strip().lower()
            if not relative:
                errors.append(f"{manifest}:{line_number}: row has an empty path")
                rows.append(("(empty path)", "FAIL: empty path"))
                continue
            target = root / relative
            if not target.is_file():
                errors.append(f"{relative}: file is missing under {root}")
                rows.append((relative, "FAIL: missing"))
                continue
            data = target.read_bytes()
            actual_hash = hashlib.sha256(data).hexdigest()
            if actual_hash != expected_hash:
                errors.append(
                    f"{relative}: contents changed since the freeze "
                    f"(manifest SHA-256 {expected_hash or '(blank)'}, actual {actual_hash})"
                )
                rows.append((relative, "FAIL: hash mismatch"))
                continue
            if size_column is not None and (record.get(size_column) or "").strip():
                expected_size = (record.get(size_column) or "").strip()
                if str(len(data)) != expected_size:
                    errors.append(
                        f"{relative}: size changed since the freeze "
                        f"(manifest {expected_size} bytes, actual {len(data)})"
                    )
                    rows.append((relative, "FAIL: size mismatch"))
                    continue
            rows.append((relative, "PASS"))
    return rows, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    manifest = args.manifest.resolve()
    root = args.root.resolve()
    if not manifest.is_file():
        print(f"Manifest not found: {manifest}", file=sys.stderr)
        return 1
    try:
        rows, errors = verify_manifest(manifest, root)
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        print(f"Could not read the manifest: {exc}", file=sys.stderr)
        return 1
    width = max((len(path) for path, _verdict in rows), default=4)
    for path, verdict in rows:
        print(f"{path.ljust(width)}  {verdict}")
    if errors:
        print(f"\nFreeze verification FAILED: {len(errors)} problem(s).", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        print(
            "\nThe frozen files no longer match the manifest. Do not analyze or "
            "report from this copy until the difference is explained and logged.",
            file=sys.stderr,
        )
        return 1
    if not rows:
        print("Freeze verification FAILED: the manifest has no rows.", file=sys.stderr)
        return 1
    print(f"\nFreeze verification passed: all {len(rows)} file(s) match the manifest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
