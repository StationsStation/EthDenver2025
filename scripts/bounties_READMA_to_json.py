#!/usr/bin/env python3

import re
import json
from pathlib import Path

SPONDER_HEADER = "## "
BOUNTY_HEADER = "### "
RAW_SPONSOR_BOUNTY_DATA_FILE = "README.md"

def parse_manually_curated_md_to_json() -> None:
    """Parse manually curated markdown to json."""
    repo_root = Path(__file__).parent.parent / "bounties"
    path = repo_root / RAW_SPONSOR_BOUNTY_DATA_FILE
    assert path.exists(), path
    content = path.read_text()
    sponsors = {}
    in_sponsor_header_section = False
    bounty = None
    for line in content.splitlines():
        if line.startswith(SPONDER_HEADER):
            sponsor = line.lstrip(SPONDER_HEADER).strip()
            sponsors[sponsor] = {}
            in_sponsor_header_section = True
        elif line.startswith(BOUNTY_HEADER):
            bounty = line.strip(BOUNTY_HEADER).strip()
            sponsors[sponsor][bounty] = ""
            in_sponsor_header_section = False
        elif bounty and not in_sponsor_header_section:
            sponsors[sponsor][bounty] += line
        else: 
            assert in_sponsor_header_section

    n_sponsors = len(sponsors)
    n_bounties = sum(len(v) for k, v in sponsors.items())
    print(f"Found {n_sponsors} sponsors, with a combined {n_bounties} bounties")

    json_data = json.dumps(sponsors, indent=4)
    outpath = path.parent /  "sponsor_bounties.json"
    outpath.write_text(json_data)
    print(f"Written to {outpath}")


if __name__ == "__main__":
    parse_manually_curated_md_to_json()
