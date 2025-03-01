"""
This script is used to create environments from the bounties in the datastore.
"""

import yaml
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

SPONSOR="{sponsor}"
BOUNTY="{bounty_id}"


# for a single agent to run locally

SKILL_ASYLUM_ABCI_APP_MODELS_AGENT_PERSONA_ARGS_GITHUB_PAT="{github_pat}"
SKILL_ASYLUM_ABCI_APP_MODELS_AGENT_PERSONA_ARGS_USERNAME="{dev_name_local}"
SKILL_ASYLUM_ABCI_APP_MODELS_AGENT_PERSONA_ARGS_SPONSOR="{sponsor_local}"
SKILL_ASYLUM_ABCI_APP_MODELS_AGENT_PERSONA_ARGS_BOUNTY="{bounty_local}"
CONNECTION_TELEGRAM_WRAPPER_CONFIG_TOKEN="{telegram_token_0}"

"""


DATA_DIR = Path("data") / SPONSOR_BOUNTY_DATA

PERSONALISATION_DIR = Path("data") / "sponsor_config.yaml"

DEFAULT_DEVS = [
    "8ball030",
    "zarathustra",
    "dvilelaf",
    "david_minarsch"
]



def lookup_devs_for_project(project_name: str , data):
    """Lookup the developers for a given project."""
    # Lookup the developers for a given project
    # We can use the default developers for now

    if not data:
        raise ValueError(f"Project {project_name} not found in sponsor_config.yaml")
    
    
    data = data.get(project_name, {})
    devs = data.get("devs", [])
    if not devs:
        raise ValueError(f"No developers found for project {project_name}")

    repos = data.get("repos", [])
    if not repos:
        raise ValueError(f"No repositories found for project {project_name}")
    
    selected_devs = [DEFAULT_DEVS[0]] + devs
    if len(selected_devs) < 4:
        selected_devs += DEFAULT_DEVS[1:4]
    
    return selected_devs[:4], [json.dumps(repos)] * 4


@click.command()
@click.option("--bounty_id", type=int, required=False, default=0)
@click.option("--sponsor_id", type=str, required=False)
@click.option("--dev_index", type=int, required=False, default=0)
def create_envs_from_bounties(bounty_id: int, sponsor_id: str, dev_index: int):
    """Create environments from the bounties in the datastore."""
    # Create environments from the bounties in the datastore
    # we first read the bounties from the datastore



    sponsor_dev_config = PERSONALISATION_DIR.read_text()
    data = yaml.safe_load(sponsor_dev_config)

    devs = {}

    for sponsor, dev_data in data.items():
        selected_devs, repos = lookup_devs_for_project(sponsor, data)
        print(f"Sponsor: {sponsor}")
        print(f"Developers: {selected_devs}")
        repos_0, repos_1, repos_2, repos_3 = repos
        name_0, name_1, name_2, name_3 = selected_devs
        devs = {i: selected_devs[i] for i in range(4)}

        env_vars = ENV_TEMPLATE.format(
            github_pat=os.getenv("GITHUB_PAT"),
            telegram_token_0=os.getenv("TELEGRAM_TOKEN_0"),
            telegram_token_1=os.getenv("TELEGRAM_TOKEN_1"),
            telegram_token_2=os.getenv("TELEGRAM_TOKEN_2"),
            telegram_token_3=os.getenv("TELEGRAM_TOKEN_3"),
            dev_name_0=name_0,
            dev_name_1=name_1,
            dev_name_2=name_2,
            dev_name_3=name_3,
            dev_repos_0=repos_0,
            dev_repos_1=repos_1,
            dev_repos_2=repos_2,
            dev_repos_3=repos_3,
            dev_name_local=devs[dev_index],
            sponsor_local=sponsor_id if sponsor_id else sponsor,
            bounty_local=bounty_id,
            sponsor=sponsor if not sponsor_id else sponsor_id,
            bounty_id=bounty_id

        )
        env_file = Path("data") / "envs" 
        env_file.mkdir(parents=True, exist_ok=True)
        env_file = env_file / f"{sponsor}.env"

        with open(env_file, "w") as f:
            f.write(env_vars)
        print(f"Created environment file: {env_file}")
    

if __name__ == "__main__":
    create_envs_from_bounties()

