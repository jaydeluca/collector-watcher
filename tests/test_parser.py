"""Tests for metadata parser."""

import shutil
import tempfile
from pathlib import Path

import pytest

from collector_watcher.parser import MetadataParser


@pytest.fixture
def temp_component_dir():
    """Create a temporary component directory."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


def create_metadata_file(component_dir: Path, content: str):
    """Helper to create a metadata.yaml file."""
    metadata_path = component_dir / "metadata.yaml"
    metadata_path.write_text(content)
    return metadata_path


def test_has_metadata_true(temp_component_dir):
    """Test detecting metadata.yaml existence."""
    create_metadata_file(temp_component_dir, "type: test")
    parser = MetadataParser(temp_component_dir)
    assert parser.has_metadata() is True


def test_has_metadata_false(temp_component_dir):
    """Test detecting missing metadata.yaml."""
    parser = MetadataParser(temp_component_dir)
    assert parser.has_metadata() is False


def test_parse_type_field(temp_component_dir):
    """Test parsing the type field."""
    create_metadata_file(temp_component_dir, "type: otlp")
    parser = MetadataParser(temp_component_dir)
    metadata = parser.parse()

    assert metadata is not None
    assert metadata["type"] == "otlp"


def test_parse_status_basic(temp_component_dir):
    """Test parsing basic status fields."""
    content = """
type: test
status:
  class: receiver
  distributions: [contrib, custom]
"""
    create_metadata_file(temp_component_dir, content)
    parser = MetadataParser(temp_component_dir)
    metadata = parser.parse()

    assert metadata["status"]["class"] == "receiver"
    assert metadata["status"]["distributions"] == ["contrib", "custom"]


def test_parse_status_stability(temp_component_dir):
    """Test parsing stability levels."""
    content = """
type: test
status:
  class: receiver
  stability:
    stable: [metrics, traces]
    beta: [logs]
    alpha: [profiles]
"""
    create_metadata_file(temp_component_dir, content)
    parser = MetadataParser(temp_component_dir)
    metadata = parser.parse()

    stability = metadata["status"]["stability"]
    # Should be sorted alphabetically by level
    assert list(stability.keys()) == ["alpha", "beta", "stable"]
    # Signals within each level should be sorted
    assert stability["stable"] == ["metrics", "traces"]
    assert stability["beta"] == ["logs"]
    assert stability["alpha"] == ["profiles"]


def test_parse_status_unsupported_platforms(temp_component_dir):
    """Test parsing unsupported platforms with sorting."""
    content = """
type: test
status:
  class: receiver
  unsupported_platforms: [windows, linux, darwin]
"""
    create_metadata_file(temp_component_dir, content)
    parser = MetadataParser(temp_component_dir)
    metadata = parser.parse()

    # Should be sorted
    assert metadata["status"]["unsupported_platforms"] == ["darwin", "linux", "windows"]


def test_parse_attributes(temp_component_dir):
    """Test parsing attributes with deterministic ordering."""
    content = """
type: test
attributes:
  zebra_attr:
    description: Last alphabetically
    type: string
  alpha_attr:
    description: First alphabetically
    type: int
  middle_attr:
    description: Middle alphabetically
    type: string
    enum: [z_value, a_value, m_value]
"""
    create_metadata_file(temp_component_dir, content)
    parser = MetadataParser(temp_component_dir)
    metadata = parser.parse()

    attrs = metadata["attributes"]
    # Attributes should be sorted by key
    assert list(attrs.keys()) == ["alpha_attr", "middle_attr", "zebra_attr"]
    # Enum values should be sorted
    assert attrs["middle_attr"]["enum"] == ["a_value", "m_value", "z_value"]


def test_parse_metrics(temp_component_dir):
    """Test parsing metrics with deterministic ordering."""
    content = """
type: test
metrics:
  system.cpu.usage:
    description: CPU usage
    unit: "%"
    enabled: true
    sum:
      monotonic: false
      aggregation_temporality: cumulative
      value_type: double
    attributes: [state, cpu]
  system.memory.usage:
    description: Memory usage
    unit: By
    enabled: true
    gauge:
      value_type: int
"""
    create_metadata_file(temp_component_dir, content)
    parser = MetadataParser(temp_component_dir)
    metadata = parser.parse()

    metrics = metadata["metrics"]
    # Metrics should be sorted by key
    assert list(metrics.keys()) == ["system.cpu.usage", "system.memory.usage"]
    # Metric attributes should be sorted
    assert metrics["system.cpu.usage"]["attributes"] == ["cpu", "state"]


def test_parse_resource_attributes(temp_component_dir):
    """Test parsing resource attributes."""
    content = """
type: test
resource_attributes:
  host.name:
    description: Hostname
    type: string
  service.name:
    description: Service name
    type: string
"""
    create_metadata_file(temp_component_dir, content)
    parser = MetadataParser(temp_component_dir)
    metadata = parser.parse()

    res_attrs = metadata["resource_attributes"]
    assert list(res_attrs.keys()) == ["host.name", "service.name"]


def test_parse_malformed_yaml(temp_component_dir):
    """Test handling malformed YAML."""
    content = """
type: test
status:
  class: receiver
  invalid: [unclosed list
"""
    create_metadata_file(temp_component_dir, content)
    parser = MetadataParser(temp_component_dir)
    metadata = parser.parse()

    # Should return None for malformed YAML
    assert metadata is None


def test_parse_empty_file(temp_component_dir):
    """Test handling empty metadata file."""
    create_metadata_file(temp_component_dir, "")
    parser = MetadataParser(temp_component_dir)
    metadata = parser.parse()

    assert metadata is None


def test_parse_missing_file(temp_component_dir):
    """Test parsing when file doesn't exist."""
    parser = MetadataParser(temp_component_dir)
    metadata = parser.parse()

    assert metadata is None


def test_parse_complete_metadata(temp_component_dir):
    """Test parsing a complete metadata file with all sections."""
    content = """
type: active_directory_ds
status:
  class: receiver
  stability:
    beta: [metrics]
  distributions: [contrib]
  codeowners:
    active: [pjanotti]
    seeking_new: true
  unsupported_platforms: [darwin, linux]
attributes:
  direction:
    description: The direction of data flow.
    type: string
    enum: [sent, received]
metrics:
  active_directory.ds.replication.network.io:
    description: Network data transmitted.
    unit: By
    sum:
      monotonic: true
      aggregation_temporality: cumulative
      value_type: int
    attributes: [direction]
    enabled: true
    stability:
      level: development
"""
    create_metadata_file(temp_component_dir, content)
    parser = MetadataParser(temp_component_dir)
    metadata = parser.parse()

    assert metadata is not None
    assert metadata["type"] == "active_directory_ds"
    assert metadata["status"]["class"] == "receiver"
    assert "direction" in metadata["attributes"]
    assert "active_directory.ds.replication.network.io" in metadata["metrics"]


def test_deterministic_output(temp_component_dir):
    """Test that parsing the same file twice produces identical output."""
    content = """
type: test
status:
  class: receiver
  stability:
    stable: [traces, metrics]
    beta: [logs]
attributes:
  z_attr:
    type: string
  a_attr:
    type: int
"""
    create_metadata_file(temp_component_dir, content)
    parser = MetadataParser(temp_component_dir)

    metadata1 = parser.parse()
    metadata2 = parser.parse()

    assert metadata1 == metadata2
    # Keys should be in the same order
    assert list(metadata1["attributes"].keys()) == list(metadata2["attributes"].keys())
