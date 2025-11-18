"""Tests for spelling fix functionality."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from docs_automation.fix_spelling import (
    load_component_names,
    update_frontmatter_ignore_list,
)


@pytest.fixture
def temp_inventory(tmp_path):
    """Create a temporary inventory structure for testing."""
    import yaml

    # Create inventory structure
    inventory_dir = tmp_path / "collector-metadata"
    contrib_dir = inventory_dir / "contrib"
    v140_dir = contrib_dir / "v0.140.0"
    v140_dir.mkdir(parents=True)

    # Create receiver.yaml with sample components
    receiver_data = {
        "distribution": "contrib",
        "version": "v0.140.0",
        "repository": "opentelemetry-collector-contrib",
        "component_type": "receiver",
        "components": [
            {"name": "awslambdareceiver", "has_metadata": False},
            {"name": "googlecloudpubsubreceiver", "has_metadata": False},
            {"name": "kafkareceiver", "has_metadata": True},
        ],
    }

    with open(v140_dir / "receiver.yaml", "w") as f:
        yaml.dump(receiver_data, f)

    # Create exporter.yaml with sample components
    exporter_data = {
        "distribution": "contrib",
        "version": "v0.140.0",
        "repository": "opentelemetry-collector-contrib",
        "component_type": "exporter",
        "components": [
            {"name": "kafkaexporter", "has_metadata": True},
            {"name": "prometheusexporter", "has_metadata": True},
        ],
    }

    with open(v140_dir / "exporter.yaml", "w") as f:
        yaml.dump(exporter_data, f)

    # Also create a snapshot version that should be ignored
    snapshot_dir = contrib_dir / "v0.141.0-SNAPSHOT"
    snapshot_dir.mkdir(parents=True)

    snapshot_data = {
        "distribution": "contrib",
        "version": "v0.141.0-SNAPSHOT",
        "repository": "opentelemetry-collector-contrib",
        "component_type": "receiver",
        "components": [
            {"name": "snapshotreceiver", "has_metadata": False},
        ],
    }

    with open(snapshot_dir / "receiver.yaml", "w") as f:
        yaml.dump(snapshot_data, f)

    return inventory_dir


def test_load_component_names(temp_inventory):
    """Test loading component names from inventory."""
    component_names = load_component_names(temp_inventory)

    # Should load from latest non-snapshot version
    assert "awslambdareceiver" in component_names
    assert "googlecloudpubsubreceiver" in component_names
    assert "kafkareceiver" in component_names
    assert "kafkaexporter" in component_names
    assert "prometheusexporter" in component_names

    # Should not include snapshot components
    assert "snapshotreceiver" not in component_names

    assert len(component_names) == 5


def test_update_frontmatter_with_existing_cspell_line(tmp_path):
    """Test updating frontmatter when cSpell:ignore line already exists."""
    # Create a test markdown file
    test_file = tmp_path / "test.md"
    original_content = """---
title: Test Page
description: Test description
weight: 100
cSpell:ignore: existingword anotherword
---

# Test Content

Some test content here.
"""
    test_file.write_text(original_content)

    # Add new words
    new_words = {"newword", "zebra"}
    result = update_frontmatter_ignore_list(test_file, new_words)

    assert result is True

    # Read updated content
    updated_content = test_file.read_text()

    # Should contain all words in sorted order
    assert "cSpell:ignore: anotherword existingword newword zebra" in updated_content

    # Should preserve other frontmatter
    assert "title: Test Page" in updated_content
    assert "weight: 100" in updated_content

    # Should preserve content after frontmatter
    assert "# Test Content" in updated_content
    assert "Some test content here." in updated_content


def test_update_frontmatter_without_cspell_line(tmp_path):
    """Test adding cSpell:ignore line when it doesn't exist."""
    # Create a test markdown file without cSpell:ignore
    test_file = tmp_path / "test.md"
    original_content = """---
title: Test Page
description: Test description
weight: 100
---

# Test Content

Some test content here.
"""
    test_file.write_text(original_content)

    # Add new words
    new_words = {"newword", "zebra"}
    result = update_frontmatter_ignore_list(test_file, new_words)

    assert result is True

    # Read updated content
    updated_content = test_file.read_text()

    # Should contain new cSpell:ignore line with sorted words
    assert "cSpell:ignore: newword zebra" in updated_content

    # Should preserve other frontmatter
    assert "title: Test Page" in updated_content
    assert "weight: 100" in updated_content

    # Should preserve content after frontmatter
    assert "# Test Content" in updated_content


def test_update_frontmatter_no_duplicates(tmp_path):
    """Test that adding existing words doesn't create duplicates."""
    # Create a test markdown file
    test_file = tmp_path / "test.md"
    original_content = """---
title: Test Page
cSpell:ignore: existingword anotherword
---

# Test Content
"""
    test_file.write_text(original_content)

    # Try to add words that already exist
    new_words = {"existingword", "newword"}
    result = update_frontmatter_ignore_list(test_file, new_words)

    assert result is True

    # Read updated content
    updated_content = test_file.read_text()

    # Should contain each word only once, sorted
    assert "cSpell:ignore: anotherword existingword newword" in updated_content

    # Count occurrences of "existingword" - should appear only once
    assert updated_content.count("existingword") == 1


def test_update_frontmatter_case_insensitive_sort(tmp_path):
    """Test that words are sorted case-insensitively."""
    test_file = tmp_path / "test.md"
    original_content = """---
title: Test Page
---

# Test Content
"""
    test_file.write_text(original_content)

    # Add words with mixed case
    new_words = {"Zebra", "apple", "Banana"}
    result = update_frontmatter_ignore_list(test_file, new_words)

    assert result is True

    # Read updated content
    updated_content = test_file.read_text()

    # Should be sorted case-insensitively: apple, Banana, Zebra
    assert "cSpell:ignore: apple Banana Zebra" in updated_content


def test_update_frontmatter_no_frontmatter(tmp_path):
    """Test handling file without frontmatter."""
    test_file = tmp_path / "test.md"
    original_content = """# Test Content

Some test content without frontmatter.
"""
    test_file.write_text(original_content)

    # Try to add words
    new_words = {"newword"}
    result = update_frontmatter_ignore_list(test_file, new_words)

    # Should return False since there's no frontmatter
    assert result is False

    # Content should be unchanged
    assert test_file.read_text() == original_content


def test_update_frontmatter_preserves_formatting(tmp_path):
    """Test that frontmatter formatting is preserved."""
    test_file = tmp_path / "test.md"
    original_content = """---
title: Test Page
description: |
  Multi-line
  description
weight: 100
# prettier-ignore
cSpell:ignore: existingword
---

# Test Content
"""
    test_file.write_text(original_content)

    # Add new words
    new_words = {"newword"}
    result = update_frontmatter_ignore_list(test_file, new_words)

    assert result is True

    # Read updated content
    updated_content = test_file.read_text()

    # Should preserve multi-line description
    assert "Multi-line" in updated_content
    assert "description" in updated_content

    # Should preserve prettier-ignore comment
    assert "# prettier-ignore" in updated_content

    # Should update cSpell:ignore
    assert "cSpell:ignore: existingword newword" in updated_content


def test_update_frontmatter_empty_word_set(tmp_path):
    """Test behavior when no words need to be added."""
    test_file = tmp_path / "test.md"
    original_content = """---
title: Test Page
cSpell:ignore: existingword
---

# Test Content
"""
    test_file.write_text(original_content)

    # Try to add empty set of words
    new_words = set()
    update_frontmatter_ignore_list(test_file, new_words)

    # Should still return True as the function can process the file
    # But the content should remain unchanged
    updated_content = test_file.read_text()
    assert "cSpell:ignore: existingword" in updated_content


@patch("docs_automation.fix_spelling.subprocess.run")
def test_run_cspell_parses_output_correctly(mock_run):
    """Test that cspell output is parsed correctly."""
    from docs_automation.fix_spelling import run_cspell

    # Mock cspell output
    mock_output = """content/en/docs/collector/components/receiver.md:25:4 - Unknown word (awslambdareceiver)
content/en/docs/collector/components/receiver.md:52:4 - Unknown word (googlecloudpubsubreceiver)
content/en/docs/collector/components/exporter.md:30:10 - Unknown word (kafkaexporter)
CSpell: Files checked: 5, Issues found: 3 in 2 files.
"""

    mock_run.return_value = MagicMock(stdout=mock_output, returncode=1)

    docs_repo = Path("/fake/path")
    result = run_cspell(docs_repo)

    # Should parse errors correctly
    assert "content/en/docs/collector/components/receiver.md" in result
    assert "content/en/docs/collector/components/exporter.md" in result

    receiver_words = result["content/en/docs/collector/components/receiver.md"]
    assert "awslambdareceiver" in receiver_words
    assert "googlecloudpubsubreceiver" in receiver_words

    exporter_words = result["content/en/docs/collector/components/exporter.md"]
    assert "kafkaexporter" in exporter_words


def test_integration_with_realistic_frontmatter(tmp_path):
    """Test with realistic frontmatter from actual collector docs."""
    test_file = tmp_path / "receiver.md"
    original_content = """---
title: Receivers
description: List of available OpenTelemetry Collector receivers
weight: 100
# prettier-ignore
cSpell:ignore: activedirectorydsreceiver aerospikereceiver apachereceiver awscloudwatchreceiver
---

# Receivers

{{< collector-components/table component="receiver" >}}
"""
    test_file.write_text(original_content)

    # Add new component names
    new_words = {"awslambdareceiver", "googlecloudpubsubreceiver", "yanggrpcreceiver"}
    result = update_frontmatter_ignore_list(test_file, new_words)

    assert result is True

    # Read updated content
    updated_content = test_file.read_text()

    # Should contain all words in sorted order
    assert "activedirectorydsreceiver" in updated_content
    assert "awslambdareceiver" in updated_content
    assert "googlecloudpubsubreceiver" in updated_content
    assert "yanggrpcreceiver" in updated_content

    # Verify they're on the same line as cSpell:ignore
    lines = updated_content.split("\n")
    cspell_line = [line for line in lines if "cSpell:ignore:" in line][0]

    # All words should be on the same line
    assert "activedirectorydsreceiver" in cspell_line
    assert "awslambdareceiver" in cspell_line
    assert "googlecloudpubsubreceiver" in cspell_line
    assert "yanggrpcreceiver" in cspell_line

    # Should preserve other content
    assert "# prettier-ignore" in updated_content
    assert '{{< collector-components/table component="receiver" >}}' in updated_content
