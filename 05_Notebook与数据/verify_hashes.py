"""Verify the current technical snapshot against every recorded SHA-256."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = PACKAGE_ROOT / "07_文档" / "当前技术版本清单.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> int:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    failures: list[str] = []
    checked = 0
    actual_groups: dict[str, list[dict[str, str]]] = {}
    for role, records in payload["source_groups"].items():
        actual_groups[role] = []
        for record in records:
            path = PACKAGE_ROOT / Path(record["path"])
            actual = sha256(path) if path.is_file() else "MISSING"
            checked += 1
            if actual != record["sha256"]:
                failures.append(f"{record['path']}: expected {record['sha256']}, actual {actual}")
            actual_groups[role].append({"path": record["path"], "sha256": actual})
    for record in payload["evidence"]["files"]:
        path = PACKAGE_ROOT / Path(record["path"])
        actual = sha256(path) if path.is_file() else "MISSING"
        checked += 1
        if actual != record["sha256"]:
            failures.append(f"{record['path']}: expected {record['sha256']}, actual {actual}")

    tree = hashlib.sha256()
    for role in sorted(actual_groups):
        for record in sorted(actual_groups[role], key=lambda row: row["path"].lower()):
            tree.update(f"{role}\0{record['path']}\0{record['sha256']}\n".encode("utf-8"))
    actual_tree = tree.hexdigest().upper()
    if actual_tree != payload["source_tree_sha256"]:
        failures.append(
            f"source_tree_sha256: expected {payload['source_tree_sha256']}, actual {actual_tree}"
        )

    print(f"SNAPSHOT_ID={payload['snapshot_id']}")
    print(f"CHECKED_HASHES={checked}")
    print(f"SOURCE_TREE_SHA256={actual_tree}")
    if failures:
        print("HASH_STATUS=FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("HASH_STATUS=PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
