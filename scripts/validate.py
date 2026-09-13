#!/usr/bin/env python3
"""Validate Star Wars Topps catalog JSON files against their schemas."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError:
    print(
        "Missing dependency: install it with "
        "'python -m pip install -r requirements.txt'.",
        file=sys.stderr,
    )
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "schema" / "card.schema.json"
DEFAULT_COLLECTION_SCHEMA = ROOT / "schema" / "collection.schema.json"
DEFAULT_CARDS = ROOT / "data" / "cards"
DEFAULT_COLLECTIONS = ROOT / "data" / "collections"


def json_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(path.rglob("*.json"))
    raise FileNotFoundError(f"Path does not exist: {path}")


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def format_location(parts: Iterable[object]) -> str:
    location = "$"
    for part in parts:
        location += f"[{part}]" if isinstance(part, int) else f".{part}"
    return location


def validate_paths(paths: list[Path], schema_path: Path = DEFAULT_SCHEMA) -> int:
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Schema error: {error}", file=sys.stderr)
        return 2

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    failures = 0

    for path in paths:
        try:
            card = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            print(f"ERROR {display_path(path)}: {error}")
            failures += 1
            continue

        errors = sorted(validator.iter_errors(card), key=lambda item: list(item.path))
        if errors:
            failures += 1
            print(f"ERROR {display_path(path)}")
            for error in errors:
                print(f"  {format_location(error.absolute_path)}: {error.message}")
        else:
            print(f"OK    {display_path(path)}")

    if failures:
        print(f"\nValidation failed: {failures} of {len(paths)} file(s) invalid.")
        return 1

    print(f"\nValidation passed: {len(paths)} file(s) valid.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Card file or directory (defaults to data/cards).",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        help="JSON Schema path (card schema by default when paths are supplied).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.paths and not args.schema:
        print("Cards")
        card_status = validate_paths(json_files(DEFAULT_CARDS), DEFAULT_SCHEMA)
        print("\nCollections")
        collection_status = validate_paths(
            json_files(DEFAULT_COLLECTIONS), DEFAULT_COLLECTION_SCHEMA
        )
        return max(card_status, collection_status)

    targets = args.paths or [DEFAULT_CARDS]
    try:
        files = sorted({file.resolve() for target in targets for file in json_files(target)})
    except FileNotFoundError as error:
        print(error, file=sys.stderr)
        return 2
    return validate_paths(files, args.schema or DEFAULT_SCHEMA)


if __name__ == "__main__":
    raise SystemExit(main())
