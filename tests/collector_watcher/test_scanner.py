"""Tests for component scanner."""

import shutil
import tempfile
from pathlib import Path

import pytest

from collector_watcher.scanner import ComponentScanner


@pytest.fixture
def mock_repo():
    """Create a temporary mock repository structure."""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)

    # Create component directories with various scenarios
    # Receiver with metadata
    receiver_with_meta = repo_path / "receiver" / "otlpreceiver"
    receiver_with_meta.mkdir(parents=True)
    (receiver_with_meta / "go.mod").touch()
    (receiver_with_meta / "metadata.yaml").write_text("type: otlp")

    # Receiver without metadata
    receiver_no_meta = repo_path / "receiver" / "customreceiver"
    receiver_no_meta.mkdir(parents=True)
    (receiver_no_meta / "go.mod").touch()

    # Processor with metadata
    processor_with_meta = repo_path / "processor" / "batchprocessor"
    processor_with_meta.mkdir(parents=True)
    (processor_with_meta / "go.mod").touch()
    (processor_with_meta / "metadata.yaml").write_text("type: batch")

    # Exporter without go.mod but with .go files
    exporter_go_files = repo_path / "exporter" / "loggingexporter"
    exporter_go_files.mkdir(parents=True)
    (exporter_go_files / "exporter.go").touch()
    (exporter_go_files / "metadata.yaml").write_text("type: logging")

    # Internal directory (should be ignored)
    internal_dir = repo_path / "receiver" / "internal"
    internal_dir.mkdir(parents=True)
    (internal_dir / "go.mod").touch()

    # Testdata directory (should be ignored)
    testdata_dir = repo_path / "processor" / "testdata"
    testdata_dir.mkdir(parents=True)
    (testdata_dir / "go.mod").touch()

    # Hidden directory (should be ignored)
    hidden_dir = repo_path / "exporter" / ".hidden"
    hidden_dir.mkdir(parents=True)
    (hidden_dir / "go.mod").touch()

    yield repo_path

    # Cleanup
    shutil.rmtree(temp_dir)


def test_scan_receivers(mock_repo):
    scanner = ComponentScanner(str(mock_repo))
    receivers = scanner.scan_component_type("receiver")

    assert len(receivers) == 2
    assert any(r["name"] == "otlpreceiver" for r in receivers)
    assert any(r["name"] == "customreceiver" for r in receivers)
    assert not any(r["name"] == "internal" for r in receivers)


def test_scan_processors(mock_repo):
    scanner = ComponentScanner(str(mock_repo))
    processors = scanner.scan_component_type("processor")

    assert len(processors) == 1
    assert processors[0]["name"] == "batchprocessor"
    assert not any(p["name"] == "testdata" for p in processors)


def test_scan_exporters(mock_repo):
    scanner = ComponentScanner(str(mock_repo))
    exporters = scanner.scan_component_type("exporter")

    assert len(exporters) == 1
    assert exporters[0]["name"] == "loggingexporter"
    assert not any(e["name"] == ".hidden" for e in exporters)


def test_metadata_detection(mock_repo):
    scanner = ComponentScanner(str(mock_repo))
    components = scanner.scan_all_components()

    otlp = next(r for r in components["receiver"] if r["name"] == "otlpreceiver")
    assert "metadata" in otlp

    custom = next(r for r in components["receiver"] if r["name"] == "customreceiver")
    assert custom.get("has_metadata") is False

    batch = next(p for p in components["processor"] if p["name"] == "batchprocessor")
    assert "metadata" in batch

    logging = next(e for e in components["exporter"] if e["name"] == "loggingexporter")
    assert "metadata" in logging


def test_scan_all_components(mock_repo):
    """Test scanning all component types."""
    scanner = ComponentScanner(str(mock_repo))
    components = scanner.scan_all_components()

    assert "receiver" in components
    assert "processor" in components
    assert "exporter" in components
    assert len(components["receiver"]) == 2
    assert len(components["processor"]) == 1
    assert len(components["exporter"]) == 1
