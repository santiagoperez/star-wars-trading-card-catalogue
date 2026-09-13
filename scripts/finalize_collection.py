#!/usr/bin/env python3
"""Validate and finalize every card template in a collection."""

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

from add_collection import prompt_integer, prompt_text, release_year, slug


ROOT = Path(__file__).resolve().parents[1]


def format_location(parts: Iterable[object]) -> str:
    location = "$"
    for part in parts:
        location += f"[{part}]" if isinstance(part, int) else f".{part}"
    return location


def load_schema(path: Path) -> Draft202012Validator:
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value must be an object")
    return value


def relative(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def schema_errors(
    path: Path,
    value: dict[str, object],
    validator: Draft202012Validator,
    root: Path,
) -> list[str]:
    return [
        f"{relative(path, root)} {format_location(error.absolute_path)}: {error.message}"
        for error in sorted(validator.iter_errors(value), key=lambda item: list(item.path))
    ]


def confirm_finalization() -> bool:
    while True:
        answer = input("Rename all templates to .json? [y/N]: ").strip().casefold()
        if answer in {"y", "yes"}:
            return True
        if answer in {"", "n", "no"}:
            return False
        print("Enter y or n.")


def finalize_collection(
    root: Path,
    year: int,
    name: str,
    dry_run: bool,
    require_confirmation: bool,
) -> int:
    collection_slug = slug(name)
    if not collection_slug:
        raise ValueError("collection name cannot form a valid id")
    collection_id = f"{year}-{collection_slug}"
    collection_path = root / "data" / "collections" / f"{collection_id}.json"
    card_directory = root / "data" / "cards" / str(year) / collection_slug

    if not collection_path.is_file():
        raise FileNotFoundError(f"collection file not found: {collection_path}")
    if not card_directory.is_dir():
        raise FileNotFoundError(f"card directory not found: {card_directory}")

    card_validator = load_schema(root / "schema" / "card.schema.json")
    collection_validator = load_schema(root / "schema" / "collection.schema.json")
    errors: list[str] = []

    try:
        collection = read_json(collection_path)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"cannot read {collection_path}: {error}") from error
    errors.extend(schema_errors(collection_path, collection, collection_validator, root))
    if collection.get("id") != collection_id:
        errors.append(
            f"{relative(collection_path, root)} $.id: expected {collection_id!r}"
        )

    templates = sorted(card_directory.glob("*.json.template"))
    if not templates:
        raise ValueError(f"no .json.template files found in {card_directory}")

    existing_paths = sorted(card_directory.glob("*.json"))
    expected_count = collection.get("base_card_count")
    if isinstance(expected_count, int) and len(existing_paths) + len(templates) != expected_count:
        errors.append(
            f"{relative(card_directory, root)}: found {len(existing_paths)} finalized "
            f"card(s) and {len(templates)} template(s), but the collection declares "
            f"{expected_count} base card(s)"
        )

    existing_ids: set[str] = set()
    for existing_path in existing_paths:
        try:
            existing = read_json(existing_path)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            errors.append(f"{relative(existing_path, root)}: cannot read JSON: {error}")
            continue
        existing_id = existing.get("id")
        if isinstance(existing_id, str):
            existing_ids.add(existing_id)

    planned: list[tuple[Path, Path]] = []
    template_ids: set[str] = set()
    for source in templates:
        destination = source.with_suffix("")
        planned.append((source, destination))
        if destination.exists():
            errors.append(
                f"{relative(source, root)}: destination already exists: "
                f"{relative(destination, root)}"
            )

        try:
            card = read_json(source)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            errors.append(f"{relative(source, root)}: cannot read JSON: {error}")
            continue

        errors.extend(schema_errors(source, card, card_validator, root))
        card_id = card.get("id")
        if isinstance(card_id, str):
            if card_id in template_ids:
                errors.append(f"{relative(source, root)} $.id: duplicate id {card_id!r}")
            if card_id in existing_ids:
                errors.append(
                    f"{relative(source, root)} $.id: id already exists in a finalized card"
                )
            template_ids.add(card_id)
        if card.get("year") != collection.get("year"):
            errors.append(
                f"{relative(source, root)} $.year: does not match the collection"
            )
        if card.get("collection") != collection.get("name"):
            errors.append(
                f"{relative(source, root)} $.collection: does not match the collection"
            )
        if not isinstance(card_id, str) or not card_id.startswith(f"{collection_id}-"):
            errors.append(
                f"{relative(source, root)} $.id: must start with {collection_id + '-'!r}"
            )

    if errors:
        print(f"Validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        print("No files were renamed.", file=sys.stderr)
        return 1

    print(f"Validation passed for {len(templates)} template(s).")
    print(f"Collection: {collection_id}")
    print(f"Directory: {relative(card_directory, root)}")
    if dry_run:
        print("Dry run complete; no files were renamed.")
        return 0
    if require_confirmation and not confirm_finalization():
        print("Cancelled; no files were renamed.")
        return 0

    renamed: list[tuple[Path, Path]] = []
    try:
        for source, destination in planned:
            source.rename(destination)
            renamed.append((source, destination))
    except OSError:
        for source, destination in reversed(renamed):
            if destination.exists() and not source.exists():
                destination.rename(source)
        raise

    print(f"Finalized {len(renamed)} card file(s).")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("year", nargs="?", type=release_year, help="Collection release year.")
    parser.add_argument("name", nargs="?", help="Collection name.")
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repository root (defaults to the parent of scripts/).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and preview without renaming files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    supplied = (args.year is not None, args.name is not None)
    if any(supplied) and not all(supplied):
        print(
            "Provide year and name together, or omit both to use interactive mode.",
            file=sys.stderr,
        )
        return 2

    interactive = not any(supplied)
    try:
        if interactive:
            print("Finalize a Star Wars Topps collection\n")
            args.year = prompt_integer("Release year", release_year)
            args.name = prompt_text("Collection name")
        return finalize_collection(
            root=args.root.resolve(),
            year=args.year,
            name=args.name,
            dry_run=args.dry_run,
            require_confirmation=interactive,
        )
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled; no files were renamed.", file=sys.stderr)
        return 1
    except (OSError, ValueError) as error:
        print(f"Finalization failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
