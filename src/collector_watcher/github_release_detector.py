"""GitHub API-based release detection for OpenTelemetry Collector repositories."""

import os
from typing import Literal

from github import Auth, Github, GithubException
from github.GitRelease import GitRelease

from .version_detector import Version

DistributionName = Literal["core", "contrib"]


class GithubReleaseDetector:
    """Detects latest releases using GitHub API instead of git tags."""

    REPO_NAMES = {
        "core": "open-telemetry/opentelemetry-collector",
        "contrib": "open-telemetry/opentelemetry-collector-contrib",
    }

    def __init__(self, github_token: str | None = None):
        """
        Initialize the GitHub release detector.

        Args:
            github_token: GitHub personal access token (optional, but recommended for rate limits)
                         If not provided, will try to read from GITHUB_TOKEN env var
        """
        token = github_token or os.environ.get("GITHUB_TOKEN")
        if token:
            auth = Auth.Token(token)
            self.github = Github(auth=auth)
        else:
            self.github = Github()

    def get_latest_release_object(self, distribution: DistributionName) -> GitRelease | None:
        """
        Get the latest release object from GitHub API.

        Args:
            distribution: Distribution name ("core" or "contrib")

        Returns:
            Latest release object, or None if no releases found

        Raises:
            GithubException: If API call fails
        """
        repo_name = self.REPO_NAMES[distribution]

        try:
            repo = self.github.get_repo(repo_name)
            return repo.get_latest_release()

        except GithubException as e:
            if e.status == 404:
                # No releases found
                return None
            raise

    def get_latest_release(self, distribution: DistributionName) -> Version | None:
        """
        Get the latest release version from GitHub API.

        Args:
            distribution: Distribution name ("core" or "contrib")

        Returns:
            Latest version, or None if no releases found

        Raises:
            GithubException: If API call fails
        """
        release = self.get_latest_release_object(distribution)
        if release is None:
            return None

        # Parse version from tag name
        return Version.from_string(release.tag_name)

    def get_all_releases(
        self, distribution: DistributionName, max_count: int = 100
    ) -> list[Version]:
        """
        Get all release versions from GitHub API.

        Args:
            distribution: Distribution name ("core" or "contrib")
            max_count: Maximum number of releases to fetch (default: 100)

        Returns:
            List of versions, sorted newest to oldest
        """
        repo_name = self.REPO_NAMES[distribution]

        try:
            repo = self.github.get_repo(repo_name)
            releases = repo.get_releases()

            versions = []
            for release in releases[:max_count]:
                try:
                    version = Version.from_string(release.tag_name)
                    if not version.is_snapshot:
                        versions.append(version)
                except ValueError:
                    # Skip invalid version tags
                    continue

            return sorted(versions, reverse=True)

        except GithubException:
            return []
