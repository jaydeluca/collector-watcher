"""Tests for version detection."""

import pytest

from collector_watcher.version_detector import Version


class TestVersion:
    """Test Version class."""

    def test_from_string_basic(self):
        """Test parsing basic version strings."""
        v = Version.from_string("v0.112.0")
        assert v.major == 0
        assert v.minor == 112
        assert v.patch == 0
        assert not v.is_snapshot

    def test_from_string_without_v(self):
        """Test parsing version without leading v."""
        v = Version.from_string("0.112.0")
        assert v.major == 0
        assert v.minor == 112
        assert v.patch == 0

    def test_from_string_snapshot(self):
        """Test parsing snapshot version."""
        v = Version.from_string("v0.113.0-SNAPSHOT")
        assert v.major == 0
        assert v.minor == 113
        assert v.patch == 0
        assert v.is_snapshot

    def test_from_string_invalid(self):
        """Test parsing invalid version raises error."""
        with pytest.raises(ValueError):
            Version.from_string("invalid")

    def test_str(self):
        """Test string representation."""
        v = Version(0, 112, 0)
        assert str(v) == "v0.112.0"

    def test_str_snapshot(self):
        """Test string representation of snapshot."""
        v = Version(0, 113, 0, is_snapshot=True)
        assert str(v) == "v0.113.0-SNAPSHOT"

    def test_comparison_major(self):
        """Test version comparison by major version."""
        v1 = Version(0, 112, 0)
        v2 = Version(1, 0, 0)
        assert v1 < v2

    def test_comparison_minor(self):
        """Test version comparison by minor version."""
        v1 = Version(0, 112, 0)
        v2 = Version(0, 113, 0)
        assert v1 < v2

    def test_comparison_patch(self):
        """Test version comparison by patch version."""
        v1 = Version(0, 112, 0)
        v2 = Version(0, 112, 1)
        assert v1 < v2

    def test_comparison_snapshot(self):
        """Test that snapshots are less than releases."""
        v1 = Version(0, 113, 0, is_snapshot=True)
        v2 = Version(0, 113, 0, is_snapshot=False)
        assert v1 < v2

    def test_equality(self):
        """Test version equality."""
        v1 = Version(0, 112, 0)
        v2 = Version(0, 112, 0)
        assert v1 == v2

    def test_next_patch(self):
        """Test getting next patch version."""
        v = Version(0, 112, 0)
        next_v = v.next_patch()
        assert next_v.major == 0
        assert next_v.minor == 112
        assert next_v.patch == 1
