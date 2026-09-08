#!/usr/bin/env python3
"""Validate wheel archives before they are published to the simple index."""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path


def validate_wheel(path: Path) -> list[str]:
    """Return a list of validation errors (empty if the wheel is OK)."""
    errors: list[str] = []
    if path.suffix != ".whl":
        errors.append(f"{path.name}: not a .whl file")
        return errors
    if path.stat().st_size == 0:
        errors.append(f"{path.name}: empty file")
        return errors
    try:
        with zipfile.ZipFile(path) as archive:
            bad_member = archive.testzip()
            if bad_member is not None:
                errors.append(f"{path.name}: corrupt zip member {bad_member!r}")
            if not any(name.endswith(".dist-info/WHEEL") for name in archive.namelist()):
                errors.append(f"{path.name}: missing .dist-info/WHEEL metadata")
    except zipfile.BadZipFile as exc:
        errors.append(f"{path.name}: bad zip file ({exc})")
    return errors


def collect_wheels(paths: list[Path]) -> list[Path]:
    wheels: list[Path] = []
    for path in paths:
        if path.is_dir():
            wheels.extend(sorted(path.glob("*.whl")))
        elif path.is_file() and path.suffix == ".whl":
            wheels.append(path)
        else:
            raise SystemExit(f"not a wheel file or directory: {path}")
    if not wheels:
        raise SystemExit("no wheels found to validate")
    return wheels


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Wheel files or directories containing *.whl",
    )
    args = parser.parse_args()

    wheels = collect_wheels(args.paths)
    failures: list[str] = []
    for wheel in wheels:
        wheel_errors = validate_wheel(wheel)
        if wheel_errors:
            failures.extend(wheel_errors)
            print(f"  FAIL  {wheel.name}")
            for message in wheel_errors:
                print(f"        {message}")
        else:
            print(f"  OK    {wheel.name} ({wheel.stat().st_size} bytes)")

    print(f"\nchecked {len(wheels)} wheel(s)")

    if failures:
        print("\nvalidation failed:", file=sys.stderr)
        for message in failures:
            print(f"  - {message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
