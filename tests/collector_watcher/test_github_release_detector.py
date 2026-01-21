"""Tests for GitHub release detector."""

import pytest

from collector_watcher.github_release_detector import GithubReleaseDetector
from collector_watcher.version_detector import Version


class TestGithubReleaseDetector:
    """Test suite for GitHub release detector."""

    def test_get_latest_release_core(self):
        """Test fetching latest release for core repository."""
        detector = GithubReleaseDetector()
        version = detector.get_latest_release("core")

        assert version is not None
        assert isinstance(version, Version)
        assert not version.is_snapshot
        # OpenTelemetry Collector uses v0.x.y format
        assert version.major == 0
        assert version.minor > 0

    def test_get_latest_release_contrib(self):
        """Test fetching latest release for contrib repository."""
        detector = GithubReleaseDetector()
        version = detector.get_latest_release("contrib")

        assert version is not None
        assert isinstance(version, Version)
        assert not version.is_snapshot
        assert version.major == 0
        assert version.minor > 0

    def test_get_all_releases(self):
        """Test fetching multiple releases."""
        detector = GithubReleaseDetector()
        versions = detector.get_all_releases("core", max_count=5)

        assert len(versions) > 0
        assert len(versions) <= 5
        # Should be sorted newest to oldest
        for i in range(len(versions) - 1):
            assert versions[i] >= versions[i + 1]