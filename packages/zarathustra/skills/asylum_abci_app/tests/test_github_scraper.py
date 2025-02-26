"""Tests for the GitHub scraper functionality."""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from packages.zarathustra.skills.asylum_abci_app.scraper import GitHubScraper


# Load environment variables from .env file
load_dotenv()

# Define test data directory
TEST_DATA_DIR = Path(__file__).parent / "data"


def test_scrape_user_interactions():
    """Test the GitHub scraper with real data."""
    # Verify GitHub token is available
    assert os.getenv("GITHUB_PAT"), "GITHUB_PAT environment variable is not set"

    # Ensure test directory exists
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize scraper
    scraper = GitHubScraper(data_dir=str(TEST_DATA_DIR))

    # Test data
    usernames = ["8ball030"]
    repos = ["https://github.com/valory-xyz/open-autonomy"]

    all_user_data = scraper.scrape_user_interactions(usernames, repos, save=True)

    assert isinstance(all_user_data, dict)
    assert all(username in all_user_data for username in usernames)

    for username in usernames:
        user_issues = all_user_data[username]
        assert isinstance(user_issues, dict)

        # Verify data was saved correctly
        user_dir = TEST_DATA_DIR / username
        assert user_dir.exists()
        assert any(str(file).endswith(".json") for file in user_dir.iterdir())

        # Verify data structure if issues were found
        if user_issues:
            issue = next(iter(user_issues.values()))
            assert all(key in issue for key in ["title", "body", "state", "created_at", "comments"])

            if issue["comments"]:
                comment = issue["comments"][0]
                assert all(key in comment for key in ["author", "body"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
