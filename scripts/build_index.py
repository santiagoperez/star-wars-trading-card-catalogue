#!/usr/bin/env python3
"""Build derived catalog files from the individual source card files."""

from __future__ import annotations

import json
from pathlib import Path

from validate import DEFAULT_CARDS, ROOT, json_files, validate_paths


OUTPUT_DIR = ROOT / "generated"


def main() -> int:
    files = json_files(DEFAULT_CARDS)
    validation_status = validate_paths(files)
    if validation_status:
        return validation_status

    cards = [json.loads(path.read_text(encoding="utf-8")) for path in files]
    cards.sort(key=lambda card: (card["year"], card["collection"], card["number"], card["id"]))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_path = OUTPUT_DIR / "cards.jsonl"
    index_path = OUTPUT_DIR / "search-index.json"

    with jsonl_path.open("w", encoding="utf-8", newline="\n") as output:
        for card in cards:
            output.write(json.dumps(card, ensure_ascii=False, separators=(",", ":")) + "\n")

    search_index = []
    for card in cards:
        descriptive_values = [
            card.get(field)
            for field in (
                "title",
                "section",
                "subtitle",
                "franchise",
                "insert_collection",
                "description",
                "front_description",
                "back_description",
                "species",
                "home_world",
                "location",
            )
        ]
        list_values = [
            value
            for field in ("affiliation", "notes")
            for value in card.get(field, [])
        ]
        search_index.append(
            {
                "id": card["id"],
                "text": " ".join(
                    [value for value in descriptive_values if value] + list_values
                ),
            }
        )

    index_path.write_text(
        json.dumps(search_index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Built {len(cards)} card(s) in {jsonl_path.relative_to(ROOT)} and {index_path.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
