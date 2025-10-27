"""Update existing documentation files with generated content using markers."""

import re
from pathlib import Path
from typing import Protocol


class ContentGenerator(Protocol):
    """Protocol for content generators that provide generated content."""

    def generate_content(self) -> str:
        """Generate the content to be inserted between markers."""
        ...


class DocUpdater:
    """Updates markdown files by replacing content between marker comments."""

    def __init__(self, marker_prefix: str = "GENERATED"):
        """
        Initialize the doc updater.

        Args:
            marker_prefix: Prefix for marker comments (default: "GENERATED")
        """
        self.marker_prefix = marker_prefix

    def get_marker_pattern(self, marker_id: str) -> tuple[str, str]:
        """
        Get the begin and end marker strings for a given marker ID.

        Args:
            marker_id: Unique identifier for the marker (e.g., "receiver-table")

        Returns:
            Tuple of (begin_marker, end_marker)
        """
        begin = f"<!-- BEGIN {self.marker_prefix}: {marker_id} -->"
        end = f"<!-- END {self.marker_prefix}: {marker_id} -->"
        return begin, end

    def update_section(self, content: str, marker_id: str, new_content: str) -> tuple[str, bool]:
        """
        Update a section of content between markers.

        Args:
            content: Original markdown content
            marker_id: Marker identifier
            new_content: New content to insert between markers

        Returns:
            Tuple of (updated_content, was_updated)
            was_updated is False if markers weren't found
        """
        begin_marker, end_marker = self.get_marker_pattern(marker_id)

        # Create regex pattern to match content between markers
        # Use DOTALL to match across newlines
        pattern = re.escape(begin_marker) + r".*?" + re.escape(end_marker)
        regex = re.compile(pattern, re.DOTALL)

        # Check if markers exist
        if not regex.search(content):
            return content, False

        # Replace content between markers
        replacement = f"{begin_marker}\n{new_content}\n{end_marker}"
        updated_content = regex.sub(replacement, content)

        return updated_content, True

    def update_multiple_sections(
        self, content: str, updates: dict[str, str]
    ) -> tuple[str, dict[str, bool]]:
        """
        Update multiple sections in content.

        Args:
            content: Original markdown content
            updates: Dictionary mapping marker_id to new_content

        Returns:
            Tuple of (updated_content, results_dict)
            results_dict maps marker_id to whether it was updated
        """
        results = {}
        current_content = content

        for marker_id, new_content in updates.items():
            current_content, was_updated = self.update_section(
                current_content, marker_id, new_content
            )
            results[marker_id] = was_updated

        return current_content, results

    def update_file(
        self, file_path: Path | str, marker_id: str, new_content: str
    ) -> bool:
        """
        Update a file by replacing content between markers.

        Args:
            file_path: Path to the markdown file
            marker_id: Marker identifier
            new_content: New content to insert

        Returns:
            True if update was successful, False if markers not found

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read existing content
        original_content = file_path.read_text()

        # Update section
        updated_content, was_updated = self.update_section(
            original_content, marker_id, new_content
        )

        if not was_updated:
            return False

        # Write back to file
        file_path.write_text(updated_content)
        return True

    def update_file_multiple(
        self, file_path: Path | str, updates: dict[str, str]
    ) -> dict[str, bool]:
        """
        Update multiple sections in a file.

        Args:
            file_path: Path to the markdown file
            updates: Dictionary mapping marker_id to new_content

        Returns:
            Dictionary mapping marker_id to whether it was updated

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read existing content
        original_content = file_path.read_text()

        # Update sections
        updated_content, results = self.update_multiple_sections(original_content, updates)

        # Only write if at least one section was updated
        if any(results.values()):
            file_path.write_text(updated_content)

        return results

    def add_markers(self, content: str, marker_id: str, at_end: bool = True) -> str:
        """
        Add markers to content if they don't exist.

        Args:
            content: Original content
            marker_id: Marker identifier to add
            at_end: If True, add at end of content; if False, add at beginning

        Returns:
            Content with markers added
        """
        begin_marker, end_marker = self.get_marker_pattern(marker_id)

        # Check if markers already exist
        if begin_marker in content and end_marker in content:
            return content

        # Add markers
        marker_block = f"\n{begin_marker}\n\n{end_marker}\n"

        if at_end:
            return content + marker_block
        else:
            return marker_block + content

    def validate_markers(self, content: str) -> dict[str, bool]:
        """
        Validate that all markers in content are properly paired.

        Args:
            content: Content to validate

        Returns:
            Dictionary mapping marker_id to whether it's valid
            (has both begin and end markers)
        """
        # Find all BEGIN markers
        begin_pattern = re.compile(
            rf"<!-- BEGIN {re.escape(self.marker_prefix)}: ([a-z0-9-]+) -->"
        )
        # Find all END markers
        end_pattern = re.compile(
            rf"<!-- END {re.escape(self.marker_prefix)}: ([a-z0-9-]+) -->"
        )

        begin_markers = set(begin_pattern.findall(content))
        end_markers = set(end_pattern.findall(content))

        results = {}

        # Check each begin marker has corresponding end
        for marker_id in begin_markers:
            results[marker_id] = marker_id in end_markers

        # Check for orphaned end markers
        for marker_id in end_markers:
            if marker_id not in begin_markers:
                results[marker_id] = False

        return results

