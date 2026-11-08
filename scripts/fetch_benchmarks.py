#!/usr/bin/env python3
"""Fetch the pinned public corpus, or verify its hashes without network access."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from urllib.request import urlopen


BENCHMARK_ROOT = Path(__file__).resolve().parents[1] / "benchmarks"


def checked_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise ValueError(f"Manifest path leaves benchmark directory: {relative}")
    return path


def verify(data: bytes, entry: dict) -> None:
    if len(data) != entry["bytes"]:
        raise ValueError(f"{entry['path']}: expected {entry['bytes']} bytes, got {len(data)}")
    digest = hashlib.sha256(data).hexdigest()
    if digest != entry["sha256"]:
        raise ValueError(f"{entry['path']}: SHA-256 mismatch ({digest})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify local files; never use the network")
    parser.add_argument("--destination", type=Path, default=BENCHMARK_ROOT,
                        help="Directory for manifest-relative file paths (default: benchmarks/)")
    args = parser.parse_args()
    manifest = json.loads((BENCHMARK_ROOT / "manifest.json").read_text())
    entries = manifest["licenses"] + manifest["benchmarks"]
    failures = 0
    for entry in entries:
        try:
            path = checked_path(args.destination, entry["path"])
            if path.exists():
                verify(path.read_bytes(), entry)
                print(f"OK {entry['path']}")
                continue
            if args.check:
                raise FileNotFoundError(f"{entry['path']}: missing")
            url = entry["url"]
            if not url.startswith("https://"):
                raise ValueError(f"Only HTTPS source URLs are allowed: {url}")
            with urlopen(url, timeout=30) as response:
                data = response.read(entry["bytes"] + 1)
            verify(data, entry)
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
                temporary = Path(output.name)
                output.write(data)
            try:
                # Link installs atomically without overwriting an existing file.
                path.hardlink_to(temporary)
            finally:
                temporary.unlink(missing_ok=True)
            print(f"FETCHED {entry['path']}")
        except (OSError, ValueError) as exc:
            failures += 1
            print(f"ERROR {exc}", file=sys.stderr)
    print(f"{len(entries) - failures}/{len(entries)} files verified")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
