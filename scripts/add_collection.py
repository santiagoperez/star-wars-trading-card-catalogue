#!/usr/bin/env python3
"""Create collection metadata and numbered card templates."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]


def slug(value: str) -> str:
    """Create a lowercase ASCII path/id component."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")


def non_negative_integer(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return number


def release_year(value: str) -> int:
    number = int(value)
    if number < 1900:
        raise argparse.ArgumentTypeError("must be 1900 or later")
    return number


def positive_integer(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be one or greater")
    return number


def checklist_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise argparse.ArgumentTypeError("must be a complete http:// or https:// URL")
    return value


def prompt_text(label: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    while True:
        value = input(f"{label}{suffix}: ").strip()
        if value:
            return value
        if default is not None:
            return default
        print("A value is required.")


def prompt_integer(
    label: str,
    converter: Callable[[str], int],
    default: int | None = None,
) -> int:
    suffix = f" [{default}]" if default is not None else ""
    while True:
        value = input(f"{label}{suffix}: ").strip()
        if not value and default is not None:
            return default
        try:
            return converter(value)
        except (TypeError, ValueError, argparse.ArgumentTypeError) as error:
            print(f"Invalid value: {error}")


def prompt_url() -> str | None:
    while True:
        value = input("Checklist URL (optional): ").strip()
        if not value:
            return None
        try:
            return checklist_url(value)
        except argparse.ArgumentTypeError as error:
            print(f"Invalid value: {error}")


def confirm_creation() -> bool:
    while True:
        value = input("Create these files? [y/N]: ").strip().casefold()
        if value in {"y", "yes"}:
            return True
        if value in {"", "n", "no"}:
            return False
        print("Enter y or n.")


def write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def scaffold_collection(
    root: Path,
    year: int,
    name: str,
    base_card_count: int,
    manufacturer: str,
    url: str | None,
    notes: list[str],
    first_number: int,
    number_width: int,
    overwrite: bool,
    dry_run: bool,
) -> tuple[Path, list[Path]]:
    name = name.strip()
    manufacturer = manufacturer.strip()
    notes = list(dict.fromkeys(note.strip() for note in notes if note.strip()))
    if year < 1900:
        raise ValueError("year must be 1900 or later")
    if base_card_count < 0:
        raise ValueError("base card count must be zero or greater")
    if first_number < 0:
        raise ValueError("first number must be zero or greater")
    if number_width < 1:
        raise ValueError("number width must be one or greater")
    if not name:
        raise ValueError("collection name cannot be empty")
    if not manufacturer:
        raise ValueError("manufacturer cannot be empty")

    collection_slug = slug(name)
    if not collection_slug:
        raise ValueError("collection name cannot form a valid id")
    collection_id = f"{year}-{collection_slug}"

    collection: dict[str, object] = {
        "id": collection_id,
        "year": year,
        "name": name,
        "manufacturer": manufacturer,
        "base_card_count": base_card_count,
    }
    if url:
        collection["checklist_url"] = url
    if notes:
        collection["notes"] = notes

    collection_path = root / "data" / "collections" / f"{collection_id}.json"
    card_directory = root / "data" / "cards" / str(year) / collection_slug
    final_number = first_number + base_card_count - 1
    width = max(number_width, len(str(final_number))) if base_card_count else number_width

    templates: list[tuple[Path, dict[str, object]]] = []
    for number in range(first_number, first_number + base_card_count):
        number_text = str(number)
        padded_number = number_text.zfill(width)
        template = {
            "id": f"{collection_id}-{padded_number}",
            "year": year,
            "collection": name,
            "number": number_text,
            "title": "",
        }
        templates.append((card_directory / f"{padded_number}.json.template", template))

    targets = [collection_path, *(path for path, _ in templates)]
    collisions = [path for path in targets if path.exists()]
    if collisions and not overwrite:
        preview = ", ".join(str(path) for path in collisions[:3])
        suffix = " ..." if len(collisions) > 3 else ""
        raise FileExistsError(
            f"refusing to overwrite {len(collisions)} existing file(s): {preview}{suffix}"
        )

    if not dry_run:
        write_json(collection_path, collection)
        for path, template in templates:
            write_json(path, template)

    action = "Would create" if dry_run else "Created"
    print(f"{action} collection: {collection_path.relative_to(root)}")
    print(f"{action} {len(templates)} card template(s) in {card_directory.relative_to(root)}")
    return collection_path, [path for path, _ in templates]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("year", nargs="?", type=release_year, help="Collection release year.")
    parser.add_argument("name", nargs="?", help="Collection name.")
    parser.add_argument(
        "base_card_count",
        nargs="?",
        type=non_negative_integer,
        help="Number of base-card templates to create.",
    )
    parser.add_argument("--manufacturer", default="Topps", help="Manufacturer name.")
    parser.add_argument("--checklist-url", type=checklist_url, help="Public checklist URL.")
    parser.add_argument(
        "--note",
        action="append",
        default=[],
        help="Collection note; repeat the option to add multiple notes.",
    )
    parser.add_argument(
        "--first-number",
        type=non_negative_integer,
        default=1,
        help="First numeric card number (default: 1).",
    )
    parser.add_argument(
        "--number-width",
        type=positive_integer,
        default=3,
        help="Minimum zero-padded template filename/id width (default: 3).",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repository root (defaults to the parent of scripts/).",
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace existing outputs.")
    parser.add_argument("--dry-run", action="store_true", help="Show outputs without writing.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    supplied = (args.year is not None, args.name is not None, args.base_card_count is not None)
    if any(supplied) and not all(supplied):
        print(
            "Provide year, name, and base_card_count together, or omit all three "
            "to use interactive mode.",
            file=sys.stderr,
        )
        return 2

    interactive = not any(supplied)
    try:
        if interactive:
            print("Create a new Star Wars Topps collection\n")
            args.year = prompt_integer("Release year", release_year)
            args.name = prompt_text("Collection name")
            args.base_card_count = prompt_integer(
                "Number of base cards", non_negative_integer
            )
            args.manufacturer = prompt_text("Manufacturer", args.manufacturer)
            if args.checklist_url is None:
                args.checklist_url = prompt_url()
            if not args.note:
                note = input("Collection note (optional): ").strip()
                if note:
                    args.note = [note]
            args.first_number = prompt_integer(
                "First card number", non_negative_integer, args.first_number
            )

            scaffold_collection(
                root=args.root.resolve(),
                year=args.year,
                name=args.name,
                base_card_count=args.base_card_count,
                manufacturer=args.manufacturer,
                url=args.checklist_url,
                notes=args.note,
                first_number=args.first_number,
                number_width=args.number_width,
                overwrite=args.overwrite,
                dry_run=True,
            )
            if args.dry_run:
                return 0
            if not confirm_creation():
                print("Cancelled; no files were created.")
                return 0

        scaffold_collection(
            root=args.root.resolve(),
            year=args.year,
            name=args.name,
            base_card_count=args.base_card_count,
            manufacturer=args.manufacturer,
            url=args.checklist_url,
            notes=args.note,
            first_number=args.first_number,
            number_width=args.number_width,
            overwrite=args.overwrite,
            dry_run=args.dry_run if not interactive else False,
        )
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled; no files were created.", file=sys.stderr)
        return 1
    except (OSError, ValueError) as error:
        print(f"Collection creation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
