"""Tests for inventory manager."""

import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from collector_watcher.inventory import InventoryManager


@pytest.fixture
def temp_inventory_dir():
    """Create a temporary directory for inventory files."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_components():
    """Sample component data for testing."""
    return {
        "receiver": [
            {"name": "otlpreceiver", "has_metadata": True},
            {"name": "customreceiver", "has_metadata": False},
        ],
        "processor": [
            {"name": "batchprocessor", "has_metadata": True},
        ],
        "exporter": [
            {"name": "loggingexporter", "has_metadata": True},
        ],
    }


def test_create_inventory(sample_components):
    """Test creating inventory structure."""
    manager = InventoryManager()
    inventory = manager.create_inventory(sample_components)

    assert inventory["repository"] == "opentelemetry-collector-contrib"
    assert inventory["components"] == sample_components


def test_create_inventory_custom_repo(sample_components):
    """Test creating inventory with custom repository name."""
    manager = InventoryManager()
    inventory = manager.create_inventory(sample_components, repository="custom-repo")

    assert inventory["repository"] == "custom-repo"


def test_save_inventory(temp_inventory_dir, sample_components):
    """Test saving inventory to file."""
    inventory_path = temp_inventory_dir / "inventory.yaml"
    manager = InventoryManager(str(inventory_path))

    inventory = manager.create_inventory(sample_components)
    manager.save_inventory(inventory)

    assert inventory_path.exists()

    # Verify file contents
    with open(inventory_path) as f:
        loaded = yaml.safe_load(f)

    assert loaded["repository"] == "opentelemetry-collector-contrib"
    assert loaded["components"]["receiver"][0]["name"] == "otlpreceiver"


def test_save_inventory_creates_directory(temp_inventory_dir, sample_components):
    """Test that save_inventory creates parent directories."""
    inventory_path = temp_inventory_dir / "nested" / "dir" / "inventory.yaml"
    manager = InventoryManager(str(inventory_path))

    inventory = manager.create_inventory(sample_components)
    manager.save_inventory(inventory)

    assert inventory_path.exists()
    assert inventory_path.parent.exists()


def test_load_inventory(temp_inventory_dir, sample_components):
    """Test loading inventory from file."""
    inventory_path = temp_inventory_dir / "inventory.yaml"
    manager = InventoryManager(str(inventory_path))

    # Save first
    inventory = manager.create_inventory(sample_components)
    manager.save_inventory(inventory)

    # Then load
    loaded = manager.load_inventory()

    assert loaded["repository"] == "opentelemetry-collector-contrib"
    assert loaded["components"] == sample_components


def test_load_nonexistent_inventory(temp_inventory_dir):
    """Test loading inventory when file doesn't exist."""
    inventory_path = temp_inventory_dir / "nonexistent.yaml"
    manager = InventoryManager(str(inventory_path))

    loaded = manager.load_inventory()

    assert loaded == {"repository": "", "components": {}}


def test_inventory_exists(temp_inventory_dir, sample_components):
    """Test checking if inventory exists."""
    inventory_path = temp_inventory_dir / "inventory.yaml"
    manager = InventoryManager(str(inventory_path))

    assert not manager.inventory_exists()

    inventory = manager.create_inventory(sample_components)
    manager.save_inventory(inventory)

    assert manager.inventory_exists()


def test_yaml_format_preserved(temp_inventory_dir, sample_components):
    """Test that YAML format is human-readable and properly formatted."""
    inventory_path = temp_inventory_dir / "inventory.yaml"
    manager = InventoryManager(str(inventory_path))

    inventory = manager.create_inventory(sample_components)
    manager.save_inventory(inventory)

    # Read as text to verify format
    with open(inventory_path) as f:
        content = f.read()

    # Should be readable YAML with proper structure
    assert "repository:" in content
    assert "components:" in content
    assert "receiver:" in content
    assert "- name:" in content
    # Should not use flow style (inline brackets)
    assert "{" not in content


def test_roundtrip_consistency(temp_inventory_dir, sample_components):
    """Test that save/load roundtrip preserves data."""
    inventory_path = temp_inventory_dir / "inventory.yaml"
    manager = InventoryManager(str(inventory_path))

    # Create and save
    original = manager.create_inventory(sample_components)
    manager.save_inventory(original)

    # Load
    loaded = manager.load_inventory()

    # Save again
    manager.save_inventory(loaded)

    # Load again
    final = manager.load_inventory()

    # Should be identical
    assert original == loaded == final
