# Star Wars Topps Catalog

A Git-friendly catalog of Star Wars Topps trading cards. Each card is stored as
an individual JSON file so edits remain easy to review and merge.

## Repository layout

```text
schema/card.schema.json     JSON Schema for card records
schema/collection.schema.json  JSON Schema for collection records
data/collections/           One metadata file per collection
data/cards/                 Source of truth: one JSON file per card
scripts/validate.py         Validate source card files
scripts/build_index.py      Build derived JSONL and search index files
scripts/import_google_sheet.py  Import an exported Google Sheets workbook
generated/                  Rebuildable output (not committed)
```

Store cards below `data/cards/<year>/<collection-slug>/<number>.json`. Card
numbers stay strings so values such as `001`, `A-12`, and `P3` are preserved.

Canonical card files contain only fields explicitly present in the mechanized
Topps source data. Search fields inferred from prose do not belong in
`data/cards/`; they can be derived later into `generated/`.

## Getting started

Python 3.10 or newer is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/validate.py
python scripts/build_index.py
```

By default, the validator checks card files against `schema/card.schema.json`
and collection files against `schema/collection.schema.json`. The index builder
validates cards first and then writes:

- `generated/cards.jsonl`: one complete card object per line
- `generated/search-index.json`: compact searchable text derived from source fields

Both files are derived artifacts and can always be recreated from the card
files.

Collection metadata lives in `data/collections/<year>-<collection-slug>.json`.
It stores shared facts such as manufacturer, base-card count, and checklist URL
without repeating them in every card record. A collection id is also the prefix
used by its card ids; for example, `2023-star-wars` owns cards beginning with
`2023-star-wars-`.

## Importing a Google Sheets tab

Download the Google Sheets workbook as an `.xlsx` file, then run:

```powershell
python scripts/import_google_sheet.py path\to\star-wars-topps.xlsx --sheet "2023 Star Wars" --dry-run
python scripts/import_google_sheet.py path\to\star-wars-topps.xlsx --sheet "2023 Star Wars"
python scripts/validate.py
```

The importer copies supported source columns into their corresponding canonical
fields. Slash-separated `Affiliation` values become an array, while values such
as `Species` and `Home World` remain source text. Blank optional fields are
omitted. Existing card files are never replaced unless `--overwrite` is
provided.

## Minimal card

```json
{
  "id": "2023-star-wars-001",
  "year": 2023,
  "collection": "Star Wars",
  "number": "1",
  "title": "Ahsoka Tano",
  "franchise": "The Mandalorian",
  "description": "Using information from Bo-Katan Kryze, Din Djarin located former Jedi Ahsoka Tano on Corvus.",
  "species": "Togruta",
  "home_world": "Unknown",
  "affiliation": ["Jedi Order", "Rebel Alliance"]
}
```

The required fields are `id`, `year`, `collection`, `number`, and `title`.
Optional fields are omitted when they do not apply; they are not stored as
`null`. Explicit source values such as `"Unknown"` are preserved.
