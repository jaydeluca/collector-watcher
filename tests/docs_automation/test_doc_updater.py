"""Tests for documentation updater."""

import tempfile
from pathlib import Path

import pytest

from docs_automation.doc_updater import DocUpdater


@pytest.fixture
def doc_updater():
    """Create a DocUpdater instance for testing."""
    return DocUpdater()


@pytest.fixture
def sample_content():
    """Sample markdown content with markers."""
    return """# Test Page

This is some manual content.

<!-- BEGIN GENERATED: test-section -->
Old generated content here
<!-- END GENERATED: test-section -->

More manual content below.
"""


class TestUpdateSection:
    """Tests for update_section method."""

    def test_update_section_basic(self, doc_updater, sample_content):
        new_content = "New generated content"
        updated, was_updated = doc_updater.update_section(
            sample_content, "test-section", new_content
        )

        assert was_updated
        # New markers include SOURCE metadata
        assert "<!-- BEGIN GENERATED: test-section SOURCE: collector-watcher -->" in updated
        assert "New generated content" in updated
        assert "Old generated content here" not in updated
        assert "This is some manual content." in updated
        assert "More manual content below." in updated

    def test_update_section_with_source_metadata(self, doc_updater):
        """Test updating content that already has SOURCE metadata."""
        content = """# Test Page

<!-- BEGIN GENERATED: test-section SOURCE: collector-watcher -->
Old content with source
<!-- END GENERATED: test-section SOURCE: collector-watcher -->

More content.
"""
        new_content = "New content"
        updated, was_updated = doc_updater.update_section(content, "test-section", new_content)

        assert was_updated
        assert "<!-- BEGIN GENERATED: test-section SOURCE: collector-watcher -->" in updated
        assert "New content" in updated
        assert "Old content with source" not in updated

    def test_update_section_backward_compatibility(self, doc_updater):
        """Test that old markers (without SOURCE) are still matched and replaced with new format."""
        old_content = """# Test Page

<!-- BEGIN GENERATED: old-section -->
Old format without source
<!-- END GENERATED: old-section -->

More content.
"""
        new_content = "Updated with new format"
        updated, was_updated = doc_updater.update_section(old_content, "old-section", new_content)

        assert was_updated
        # Old markers should be replaced with new format
        assert "<!-- BEGIN GENERATED: old-section SOURCE: collector-watcher -->" in updated
        assert "Updated with new format" in updated
        assert "Old format without source" not in updated

    def test_update_section_markers_not_found(self, doc_updater):
        content = "# Simple Page\n\nNo markers here."
        updated, was_updated = doc_updater.update_section(content, "nonexistent", "New content")

        assert not was_updated
        assert updated == content

    def test_update_section_multiline_content(self, doc_updater, sample_content):
        """Test updating with multiline content."""
        new_content = """Line 1
Line 2
Line 3"""
        updated, was_updated = doc_updater.update_section(
            sample_content, "test-section", new_content
        )

        assert was_updated
        assert "Line 1" in updated
        assert "Line 2" in updated
        assert "Line 3" in updated

    def test_update_section_preserves_surrounding_content(self, doc_updater):
        """Test that content around markers is preserved."""
        content = """Header

<!-- BEGIN GENERATED: section1 -->
Old content
<!-- END GENERATED: section1 -->

Middle text

<!-- BEGIN GENERATED: section2 -->
More old content
<!-- END GENERATED: section2 -->

Footer"""

        updated, was_updated = doc_updater.update_section(content, "section1", "New content 1")

        assert was_updated
        assert "Header" in updated
        assert "New content 1" in updated
        assert "Middle text" in updated
        assert "More old content" in updated  # section2 unchanged
        assert "Footer" in updated

    def test_update_section_empty_content(self, doc_updater, sample_content):
        """Test updating with empty content."""
        updated, was_updated = doc_updater.update_section(sample_content, "test-section", "")

        assert was_updated
        assert "<!-- BEGIN GENERATED: test-section SOURCE: collector-watcher -->" in updated
        assert "<!-- END GENERATED: test-section SOURCE: collector-watcher -->" in updated
        assert "Old generated content here" not in updated


class TestUpdateMultipleSections:
    """Tests for update_multiple_sections method."""

    def test_update_multiple_sections(self, doc_updater):
        """Test updating multiple sections."""
        content = """# Page

<!-- BEGIN GENERATED: section1 -->
Old 1
<!-- END GENERATED: section1 -->

Text

<!-- BEGIN GENERATED: section2 -->
Old 2
<!-- END GENERATED: section2 -->
"""

        updates = {"section1": "New 1", "section2": "New 2"}
        updated, results = doc_updater.update_multiple_sections(content, updates)

        assert results["section1"]
        assert results["section2"]
        assert "New 1" in updated
        assert "New 2" in updated
        assert "Old 1" not in updated
        assert "Old 2" not in updated

    def test_update_multiple_sections_partial(self, doc_updater):
        """Test updating multiple sections when some don't exist."""
        content = """# Page

<!-- BEGIN GENERATED: section1 -->
Old 1
<!-- END GENERATED: section1 -->
"""

        updates = {"section1": "New 1", "section2": "New 2"}
        updated, results = doc_updater.update_multiple_sections(content, updates)

        assert results["section1"]
        assert not results["section2"]
        assert "New 1" in updated


class TestUpdateFile:
    """Tests for update_file method."""

    def test_update_file(self, doc_updater, sample_content):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(sample_content)
            temp_path = Path(f.name)

        try:
            success = doc_updater.update_file(temp_path, "test-section", "Updated file content")

            assert success
            updated_content = temp_path.read_text()
            assert "Updated file content" in updated_content
            assert "Old generated content here" not in updated_content
        finally:
            temp_path.unlink()

    def test_update_file_not_found(self, doc_updater):
        with pytest.raises(FileNotFoundError):
            doc_updater.update_file("/nonexistent/file.md", "test", "content")


class TestUpdateFileMultiple:
    """Tests for update_file_multiple method."""

    def test_update_file_multiple(self, doc_updater):
        """Test updating multiple sections in a file."""
        content = """# Page

<!-- BEGIN GENERATED: section1 -->
Old 1
<!-- END GENERATED: section1 -->

<!-- BEGIN GENERATED: section2 -->
Old 2
<!-- END GENERATED: section2 -->
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            updates = {"section1": "New 1", "section2": "New 2"}
            results = doc_updater.update_file_multiple(temp_path, updates)

            assert results["section1"]
            assert results["section2"]

            updated_content = temp_path.read_text()
            assert "New 1" in updated_content
            assert "New 2" in updated_content
        finally:
            temp_path.unlink()
