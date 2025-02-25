"""Simple tests for the service."""

import re
from pathlib import Path

from aea.configurations.constants import DEFAULT_SERVICE_CONFIG_FILE


env_var_pattern = r"\${([A-Z0-9_]+)(?::([a-z]+))?(?::(.+?))?}"


def test_env_template_present():
    """Test that an example environment file is present."""
    env_template_path = Path(__file__).parent.parent / ".env.example"
    assert env_template_path.exists(), "Environment template file not found."


def test_example_env_contains_all_overrides():
    """Test that the example env contains all of the env vars extracted from the service config."""
    service_config = (Path(__file__).parent.parent / DEFAULT_SERVICE_CONFIG_FILE).read_text()
    env_template_path = Path(__file__).parent.parent / ".env.example"
    env_template = env_template_path.read_text()
    # we regex out all the env vars from the service config
    matches = re.findall(env_var_pattern, service_config)

    fails = []
    for key, _type, default in matches:
        if key not in env_template:
            fails.append(f"Variable {key} Type: {_type} Default: {default}")
    assert not fails, f"Missing env vars in .env.example: {fails}"
