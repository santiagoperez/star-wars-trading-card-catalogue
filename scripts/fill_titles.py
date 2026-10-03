import argparse
import json
from pathlib import Path


def load_titles(path: Path) -> list[str]:
    """Load one card title per line, preserving order."""
    with path.open("r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def main():
    parser = argparse.ArgumentParser(
        description="Populate JSON template files with card titles."
    )

    parser.add_argument(
        "titles_file",
        type=Path,
        help="Text file containing one card title per line, in card-number order.",
    )

    parser.add_argument(
        "templates_dir",
        type=Path,
        help="Directory containing the .json.template files.",
    )

    args = parser.parse_args()

    titles = load_titles(args.titles_file)

    templates = sorted(
        args.templates_dir.glob("*.json.template"),
        key=lambda p: int(p.name.split(".")[0]),
    )

    if not templates:
        raise SystemExit("No .json.template files found.")

    if len(templates) != len(titles):
        raise SystemExit(
            f"Number of titles ({len(titles)}) does not match "
            f"number of templates ({len(templates)})."
        )

    for template_path, title in zip(templates, titles):

        # Load the existing template
        with template_path.open("r", encoding="utf-8") as f:
            card = json.load(f)

        # Update ONLY the title
        card["title"] = title

        # Write back to the SAME .json.template file
        with template_path.open("w", encoding="utf-8") as f:
            json.dump(card, f, indent=2, ensure_ascii=False)
            f.write("\n")

        print(f"{template_path.name} → {title}")

    print(f"\nSuccessfully updated {len(templates)} templates.")


if __name__ == "__main__":
    main()