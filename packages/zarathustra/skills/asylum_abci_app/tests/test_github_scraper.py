"""Tests for the GitHub scraper functionality."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest
from dotenv import load_dotenv

from packages.zarathustra.skills.asylum_abci_app.scraper import GitHubScraper


# Load environment variables from .env file
load_dotenv()

# Define test data directory
TEST_DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture
def data_dir() -> Path:
    """Create a temporary directory for test data."""
    with TemporaryDirectory() as tmp_dir:
        return Path(tmp_dir)


def test_scrape_user_interactions(data_dir: Path):
    """Test the GitHub scraper with real data."""
    # Verify GitHub token is available

    gh_pat = "gh_pat"
    # Ensure test directory exists
    # Initialize scraper

    scraper = GitHubScraper(data_dir=str(data_dir), gh_pat=gh_pat)

    # Test data
    usernames = ["8ball030"]
    repos = ["https://github.com/StationsStation/EthDenver2025"]

    with (
        patch(
            "packages.zarathustra.skills.asylum_abci_app.scraper.GitHubScraper._fetch_repo_issues"
        ) as mock_get_issues,
        patch("packages.zarathustra.skills.asylum_abci_app.scraper.GitHubScraper._fetch_comments") as mock_get_comments,
    ):

        def mock_comments(*args, **kwargs):
            del args, kwargs
            return [{"author": "test", "body": "test comment"}]

        def mock_issues(*args, **kwargs):
            del args, kwargs
            return [{"title": "test", "body": "test issue", "state": "open", "created_at": "2021-01-01T00:00:00Z"}]

        mock_get_issues.side_effect = mock_issues
        mock_get_comments.side_effect = mock_comments

        all_user_data = scraper.scrape_user_interactions(usernames, repos, save=True)

    assert isinstance(all_user_data, dict)
    assert all(username in all_user_data for username in usernames)

    for username in usernames:
        user_issues = all_user_data[username]
        assert isinstance(user_issues, dict)

        # Verify data was saved correctly
        user_dir = data_dir / username
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
