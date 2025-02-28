#!/usr/bin/env python3
 
import re
from pathlib import Path

PRICE_REGEX_PATTERN = r"(?m)(?=^\$\d{1,3}(?:,\d{3})*)"
RAW_SPONSOR_BOUNTY_DATA_FILE = "ethdenver-prizes.txt"


def get_bounty_info() -> None:
    """Parse raw scrape into raw markdown. Requires manual curation."""
    repo_root = Path(__file__).parent.parent
    path = repo_root / RAW_SPONSOR_BOUNTY_DATA_FILE
    assert path.exists(), path
    content = path.read_text()
    parts = re.split(PRICE_REGEX_PATTERN, content)
    print(f"Found {len(parts)} bounties")
    formatted_data = "\n\n### ".join(part.strip() for part in parts)
    outpath = path.parent /  (path.stem + "-intermediate.md")
    outpath.write_text(formatted_data)
    print(f"Written to {outpath}")


if __name__ == "__main__":
    get_bounty_info()
