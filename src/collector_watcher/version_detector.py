"""Version detection for OpenTelemetry Collector repositories."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import git


@dataclass
class Version:
    """Represents a semantic version."""

    major: int
    minor: int
    patch: int
    is_snapshot: bool = False

    @classmethod
    def from_string(cls, version_str: str) -> "Version":
        """
        Parse a version string.

        Args:
            version_str: Version string (e.g., "v0.112.0" or "v0.113.0-SNAPSHOT")

        Returns:
            Version object

        Raises:
            ValueError: If version string is invalid
        """
        version_str = version_str.lstrip("v")

        is_snapshot = version_str.endswith("-SNAPSHOT")
        if is_snapshot:
            version_str = version_str.replace("-SNAPSHOT", "")

        match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version_str)
        if not match:
            raise ValueError(f"Invalid version string: {version_str}")

        return cls(
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3)),
            is_snapshot=is_snapshot,
        )

    def __str__(self) -> str:
        """Return string representation."""
        base = f"v{self.major}.{self.minor}.{self.patch}"
        if self.is_snapshot:
            return f"{base}-SNAPSHOT"
        return base

    def __lt__(self, other: "Version") -> bool:
        """Compare versions for sorting. Snapshots are considered less than releases."""
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        if self.patch != other.patch:
            return self.patch < other.patch
        if self.is_snapshot != other.is_snapshot:
            return self.is_snapshot
        return False

    def __le__(self, other: "Version") -> bool:
        """Less than or equal comparison."""
        return self == other or self < other

    def __gt__(self, other: "Version") -> bool:
        """Greater than comparison."""
        return not self <= other

    def __ge__(self, other: "Version") -> bool:
        """Greater than or equal comparison."""
        return not self < other

    def __eq__(self, other: object) -> bool:
        """Check equality."""
        if not isinstance(other, Version):
            return False
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.is_snapshot == other.is_snapshot
        )

    def next_patch(self) -> "Version":
        """Return next patch version."""
        return Version(self.major, self.minor, self.patch + 1)


DistributionName = Literal["core", "contrib"]


class VersionDetector:
    """Detects versions in OpenTelemetry Collector repositories."""

    def __init__(self, repo_path: str | Path, api_latest_version: Version | None = None):
        """
        Initialize the version detector.

        Args:
            repo_path: Path to the git repository
            api_latest_version: Optional pre-fetched latest version from API
        """
        self.repo_path = Path(repo_path)
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")

        self.repo = git.Repo(str(self.repo_path))
        self.api_latest_version = api_latest_version

    def get_latest_release_tag(self) -> Version | None:
        """
        Get the latest release tag from the repository.

        If an API-based version was provided during initialization, returns that.
        Otherwise, reads from git tags (requires tags to be fetched).

        Returns:
            Latest version tag, or None if no valid tags found
        """
        if self.api_latest_version is not None:
            return self.api_latest_version

        # Fallback to reading from git tags
        tags = self.repo.tags
        version_tags = []

        for tag in tags:
            try:
                version = Version.from_string(tag.name)
                if not version.is_snapshot:
                    version_tags.append(version)
            except ValueError:
                continue

        if not version_tags:
            return None

        return max(version_tags)

    def get_all_release_tags(self) -> list[Version]:
        """
        Get all release tags from the repository, sorted newest to oldest.

        Returns:
            List of version tags
        """
        tags = self.repo.tags
        version_tags = []

        for tag in tags:
            try:
                version = Version.from_string(tag.name)
                if not version.is_snapshot:
                    version_tags.append(version)
            except ValueError:
                continue

        return sorted(version_tags, reverse=True)

    def checkout_version(self, version: Version) -> None:
        """
        Checkout a specific version tag.

        Fetches the specific tag from remote if not available locally.

        Args:
            version: Version to checkout

        Raises:
            ValueError: If version tag doesn't exist
        """
        tag_name = str(version)
        try:
            # Try to checkout the tag directly first
            self.repo.git.checkout(tag_name)
        except git.exc.GitCommandError:
            # Tag doesn't exist locally, fetch it from remote
            try:
                # Fetch only the specific tag (much faster than fetching all tags)
                self.repo.git.fetch("origin", f"refs/tags/{tag_name}:refs/tags/{tag_name}")
                self.repo.git.checkout(tag_name)
            except git.exc.GitCommandError as e:
                raise ValueError(f"Failed to checkout {tag_name}: {e}") from e

    def checkout_main(self) -> None:
        """Checkout the main branch (tries master as fallback)."""
        try:
            self.repo.git.checkout("main")
        except git.exc.GitCommandError:
            try:
                self.repo.git.checkout("master")
            except git.exc.GitCommandError as e:
                raise ValueError(f"Failed to checkout main/master branch: {e}") from e

    def determine_next_snapshot_version(self) -> Version:
        """
        Determine the next snapshot version based on latest release.

        Returns:
            Next snapshot version
        """
        latest = self.get_latest_release_tag()
        if latest is None:
            return Version(0, 0, 1, is_snapshot=True)

        next_version = latest.next_patch()
        next_version.is_snapshot = True
        return next_version
