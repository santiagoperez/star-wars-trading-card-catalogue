# Star Wars Topps Catalog

A Git-friendly catalog of Star Wars Topps trading cards. Each card is stored as
an individual JSON file so edits remain easy to review and merge.

## Repository layout

```text
schema/card.schema.json     JSON Schema for card records
data/collections/           Optional collection-level metadata
data/cards/                 Source of truth: one JSON file per card
scripts/validate.py         Validate source card files
scripts/build_index.py      Build derived JSONL and search index files
scripts/import_google_sheet.py  Future Google Sheets importer
generated/                  Rebuildable output (not committed)
```

Store cards below `data/cards/<year>/<collection-slug>/<number>.json`. Card
numbers stay strings so values such as `001`, `A-12`, and `P3` are preserved.
All entity values are arrays, including `species` and `home_worlds`.

## Getting started

Python 3.10 or newer is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/validate.py
python scripts/build_index.py
```

The validator checks every `*.json` file below `data/cards/` against
`schema/card.schema.json`. The index builder validates first and then writes:

- `generated/cards.jsonl`: one complete card object per line
- `generated/search-index.json`: compact searchable text and entity data

Both files are derived artifacts and can always be recreated from the card
files.

## Minimal card

```json
{
  "id": "2023-star-wars-001",
  "year": 2023,
  "collection": "Star Wars",
  "number": "1",
  "title": "Ahsoka Tano",
  "entities": {
    "characters": ["Ahsoka Tano"],
    "locations": [],
    "home_worlds": [],
    "species": ["Togruta"],
    "organizations": ["Jedi Order"],
    "vehicles": [],
    "droids": [],
    "creatures": [],
    "concepts": ["Jedi"]
  }
}
```

Optional descriptive fields may be omitted or set to `null`. Use an empty
array instead of `"Unknown"` when an entity is not known.
