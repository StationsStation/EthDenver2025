"""GitHub issue fetching functionality."""

import json
import time
import logging
from pathlib import Path

import requests
from rich import progress
from dotenv import load_dotenv


load_dotenv()
logger = logging.getLogger(__name__)


class GitHubScraper:
    """A class to scrape GitHub issues and comments."""

    def __init__(self, gh_pat: str | None = None, data_dir: str | None = None):
        """Initialize the scraper with GitHub PAT and settings."""
        self.gh_pat = gh_pat
        if not self.gh_pat:
            msg = "GitHub PAT not found. Make sure GITHUB_PAT is set in environment or .env file"
            raise ValueError(msg)

        self.base_data_dir = Path(data_dir) if data_dir else None
        if self.base_data_dir:
            self.base_data_dir.mkdir(parents=True, exist_ok=True)

        self.headers = {
            "Authorization": f"Bearer {self.gh_pat}",
            "Accept": "application/vnd.github.v3+json",
        }
        self.timeout = 30  # seconds

    def get_user_data_dir(self, username: str) -> Path | None:
        """Get the data directory for a specific user."""
        if not self.base_data_dir:
            return None
        user_dir = self.base_data_dir / username
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def save_user_data(self, username: str, issues: dict) -> str | None:
        """Save issues data to a JSON file in user's directory."""
        user_dir = self.get_user_data_dir(username)

        filename = "repos.json"
        filepath = user_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(issues, f, indent=2, ensure_ascii=False)

        return str(filepath)

    def _fetch_comments(self, owner: str, repo_name: str, issue_number: int) -> list:
        """Fetch comments for a specific issue."""
        comments_url = f"https://api.github.com/repos/{owner}/{repo_name}/issues/{issue_number}/comments"
        response = requests.get(comments_url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _process_issue_for_users(self, issue: dict, comments: list, usernames: list[str], all_user_data: dict) -> None:
        """Process an issue and its comments for the given users."""
        issue_number = issue["number"]
        for username in usernames:
            user_commented = any(comment["user"]["login"] == username for comment in comments)
            if user_commented or issue["user"]["login"] == username:
                all_user_data[username][issue_number] = self._process_issue_data(issue, comments)

    def _fetch_repo_issues(self, owner: str, repo_name: str, usernames: list[str], all_user_data: dict) -> None:
        """Fetch and process all issues for a repository."""
        issues_url = f"https://api.github.com/repos/{owner}/{repo_name}/issues?state=all&per_page=100"
        response = requests.get(issues_url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        issues = response.json()

        for issue in progress.track(issues, description=f"Fetching issues for {owner}/{repo_name}"):
            try:
                comments = self._fetch_comments(owner, repo_name, issue["number"])
                self._process_issue_for_users(issue, comments, usernames, all_user_data)
                time.sleep(0.1)  # Respect GitHub API rate limits
            except requests.exceptions.RequestException as e:
                logger.warning(f"Error fetching comments for issue {issue['number']}: {e!s}")
                continue

    def scrape_user_interactions(self, usernames: list[str], repos: list[str], save: bool = True) -> dict:
        """Fetch all issues where specific users have interacted."""
        all_user_data = {username: {} for username in usernames}

        for repo in repos:
            # Extract owner and repo name from URL
            _, _, _, owner, repo_name = repo.rstrip("/").split("/")
            try:
                self._fetch_repo_issues(owner, repo_name, usernames, all_user_data)
            except requests.exceptions.RequestException as e:
                logger.exception(f"Error fetching data from {repo}: {e!s}")
                continue

        if save:
            for username, issues in all_user_data.items():
                self.save_user_data(username, issues)

        return all_user_data

    def _process_issue_data(self, issue: dict, comments: list) -> dict:
        """Process and structure issue data."""
        issue_data = {
            "title": issue["title"],
            "body": issue["body"],
            "state": issue["state"],
            "created_at": issue["created_at"],
            "comments": [],
        }

        # Add the initial issue body as first "comment" if it exists
        if issue["body"]:
            issue_data["comments"].append(
                {
                    "author": issue["user"]["login"],
                    "body": issue["body"],
                }
            )

        # Add all comments in chronological order
        for comment in comments:
            comment_data = {
                "author": comment["user"]["login"],
                "body": comment["body"],
            }
            issue_data["comments"].append(comment_data)

        return issue_data
