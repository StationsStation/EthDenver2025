"""
This script is used to create environments from the bounties in the datastore.
"""

from packages.zarathustra.skills.asylum_abci_app.behaviours import SPONSOR_BOUNTY_DATA
import json
from pathlib import Path
import rich_click as click
from rich import print
import os


ENV_TEMPLATE = """
PYTHONWARNINGS="ignore"
PYTHONPATH="."
GITHUB_PAT="{github_pat}"
TELEGRAM_TOKEN_0={telegram_token_0}
TELEGRAM_TOKEN_1={telegram_token_1}
TELEGRAM_TOKEN_2={telegram_token_2}
TELEGRAM_TOKEN_3={telegram_token_3}

DEV_NAME_0={dev_name_0}
DEV_NAME_1={dev_name_1}
DEV_NAME_2={dev_name_2}
DEV_NAME_3={dev_name_3}

DEV_REPOS_0={dev_repos_0}
DEV_REPOS_1={dev_repos_1}
DEV_REPOS_2={dev_repos_2}
DEV_REPOS_3={dev_repos_3}
"""


DATA_DIR = Path("data") / SPONSOR_BOUNTY_DATA

PERSONALISATION_DIR = Path("data") / "sponsor_confi.yaml"

DEFAULT_DEVS = [
    "8ball030",
    "zarathustra",
    "dvilelaf",
    "david_minarsch"
]

@click.command()
@click.option("--bounty_id", type=int, required=False)
@click.option("--sponsor", type=str, required=False)
def create_envs_from_bounties(bounty_id: int, sponsor: str):
    """Create environments from the bounties in the datastore."""
    click.echo(f"Creating environments for bounty {bounty_id} sponsored by {sponsor}")
    # Create environments from the bounties in the datastore
    # we first read the bounties from the datastore
    with open(DATA_DIR ) as f:
        bounties = json.load(f)

    total_bounties = 0
    print(f"Total Sponsors: {len(bounties)}")
    for sponsor, bounties in bounties.items():
        breakpoint()
        for bounty in bounties:
            total_bounties += 1
            
            env_vars = ENV_TEMPLATE.format(
                github_pat=os.getenv("GITHUB_PAT"),
                telegram_token_0=os.getenv("TELEGRAM_TOKEN_0"),
                telegram_token_1=os.getenv("TELEGRAM_TOKEN_1"),
                telegram_token_2=os.getenv("TELEGRAM_TOKEN_2"),
                telegram_token_3=os.getenv("TELEGRAM_TOKEN_3"),
                dev_name_0=bounty["dev_name_0"],
                dev_name_1=bounty["dev_name_1"],
                dev_name_2=bounty["dev_name_2"],
                dev_name_3=bounty["dev_name_3"],
                dev_repos_0=bounty["dev_repos_0"],
                dev_repos_1=bounty["dev_repos_1"],
                dev_repos_2=bounty["dev_repos_2"],
                dev_repos_3=bounty["dev_repos_3"],
            )
            env_file = Path("envs") / f"{bounty['id']}_{sponsor}.env"
            with open(env_file, "w") as f:
                f.write(env_vars)
            print(f"Created environment file: {env_file}")
    

if __name__ == "__main__":
    create_envs_from_bounties()

