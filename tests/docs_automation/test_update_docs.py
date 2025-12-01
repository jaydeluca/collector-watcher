"""Tests for update_docs functionality."""

import tempfile
from pathlib import Path

import pytest
import yaml

from collector_watcher.inventory import InventoryManager
from collector_watcher.version_detector import Version
from docs_automation.update_docs import get_best_available_version, merge_inventories


@pytest.fixture
def temp_inventory_dir():
    """Create a temporary inventory directory with test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create test data structure
        # Core: v0.140.0 (stable)
        core_v140_0 = tmpdir_path / "core" / "v0.140.0"
        core_v140_0.mkdir(parents=True)

        core_data = {
            "distribution": "core",
            "version": "v0.140.0",
            "repository": "opentelemetry-collector",
            "component_type": "extension",
            "components": [
                {
                    "name": "memorylimiterextension",
                    "metadata": {
                        "status": {
                            "distributions": [],
                            "stability": {"development": ["extension"]},
                        }
                    },
                }
            ],
        }

        with open(core_v140_0 / "extension.yaml", "w") as f:
            yaml.dump(core_data, f)

        # Core: v0.139.0 (older stable)
        core_v139_0 = tmpdir_path / "core" / "v0.139.0"
        core_v139_0.mkdir(parents=True)

        older_core_data = core_data.copy()
        older_core_data["version"] = "v0.139.0"

        with open(core_v139_0 / "extension.yaml", "w") as f:
            yaml.dump(older_core_data, f)

        # Contrib: v0.140.1 (stable)
        contrib_v140_1 = tmpdir_path / "contrib" / "v0.140.1"
        contrib_v140_1.mkdir(parents=True)

        contrib_data = {
            "distribution": "contrib",
            "version": "v0.140.1",
            "repository": "opentelemetry-collector-contrib",
            "component_type": "extension",
            "components": [
                {
                    "name": "ackextension",
                    "metadata": {
                        "status": {
                            "distributions": ["contrib"],
                            "stability": {"alpha": ["extension"]},
                        }
                    },
                }
            ],
        }

        with open(contrib_v140_1 / "extension.yaml", "w") as f:
            yaml.dump(contrib_data, f)

        # Contrib: v0.140.0 (older stable)
        contrib_v140_0 = tmpdir_path / "contrib" / "v0.140.0"
        contrib_v140_0.mkdir(parents=True)

        older_contrib_data = contrib_data.copy()
        older_contrib_data["version"] = "v0.140.0"

        with open(contrib_v140_0 / "extension.yaml", "w") as f:
            yaml.dump(older_contrib_data, f)

        yield tmpdir_path


class TestGetBestAvailableVersion:
    """Tests for get_best_available_version function."""

    def test_exact_version_exists(self, temp_inventory_dir):
        """Test when the exact version exists."""
        inv_mgr = InventoryManager(str(temp_inventory_dir))
        target_version = Version.from_string("v0.140.0")

        result = get_best_available_version(inv_mgr, "core", target_version)

        assert result == target_version

    def test_fallback_to_previous_version(self, temp_inventory_dir):
        """Test fallback when target version doesn't exist."""
        inv_mgr = InventoryManager(str(temp_inventory_dir))
        target_version = Version.from_string("v0.140.1")  # Doesn't exist for core

        result = get_best_available_version(inv_mgr, "core", target_version)

        # Should fall back to v0.140.0 (latest available before target)
        assert result == Version.from_string("v0.140.0")

    def test_no_versions_available(self, temp_inventory_dir):
        """Test when no versions are available."""
        inv_mgr = InventoryManager(str(temp_inventory_dir))
        target_version = Version.from_string("v0.140.0")

        # Try to get version for a distribution that doesn't exist
        with pytest.raises(ValueError, match="No versions found"):
            get_best_available_version(inv_mgr, "nonexistent", target_version)

    def test_fallback_to_oldest_when_all_newer(self, temp_inventory_dir):
        """Test fallback to oldest version when all versions are newer than target."""
        inv_mgr = InventoryManager(str(temp_inventory_dir))
        target_version = Version.from_string("v0.138.0")  # Older than available

        result = get_best_available_version(inv_mgr, "core", target_version)

        # Should return the oldest available version
        assert result == Version.from_string("v0.139.0")


class TestMergeInventories:
    """Tests for merge_inventories function."""

    def test_merge_basic(self):
        """Test basic merging of core and contrib inventories."""
        core_inventory = {
            "components": {
                "extension": [
                    {
                        "name": "memorylimiterextension",
                        "metadata": {
                            "status": {
                                "distributions": [],
                                "stability": {"development": ["extension"]},
                            }
                        },
                    }
                ]
            }
        }

        contrib_inventory = {
            "components": {
                "extension": [
                    {
                        "name": "ackextension",
                        "metadata": {
                            "status": {
                                "distributions": ["contrib"],
                                "stability": {"alpha": ["extension"]},
                            }
                        },
                    }
                ]
            }
        }

        result = merge_inventories(core_inventory, contrib_inventory)

        extensions = result["components"]["extension"]
        assert len(extensions) == 2
        assert any(e["name"] == "memorylimiterextension" for e in extensions)
        assert any(e["name"] == "ackextension" for e in extensions)

    def test_merge_overlapping_components(self):
        """Test merging when same component exists in both."""
        core_inventory = {
            "components": {
                "receiver": [
                    {
                        "name": "otlpreceiver",
                        "metadata": {
                            "status": {
                                "distributions": ["core"],
                                "stability": {"stable": ["traces", "metrics", "logs"]},
                            }
                        },
                    }
                ]
            }
        }

        contrib_inventory = {
            "components": {
                "receiver": [
                    {
                        "name": "otlpreceiver",
                        "metadata": {
                            "status": {
                                "distributions": ["contrib"],
                                "stability": {"stable": ["traces", "metrics", "logs"]},
                            }
                        },
                    }
                ]
            }
        }

        result = merge_inventories(core_inventory, contrib_inventory)

        receivers = result["components"]["receiver"]
        assert len(receivers) == 1
        receiver = receivers[0]
        assert receiver["name"] == "otlpreceiver"
        assert receiver["source_repo"] == "core"  # Should prefer core
        assert set(receiver["metadata"]["status"]["distributions"]) == {"core", "contrib"}

    def test_merge_skips_experimental_components(self):
        """Test that experimental 'x' components are skipped."""
        core_inventory = {
            "components": {
                "receiver": [
                    {
                        "name": "xreceiver",  # Experimental, should be skipped
                        "metadata": {},
                    },
                    {
                        "name": "otlpreceiver",
                        "metadata": {
                            "status": {
                                "distributions": ["core"],
                            }
                        },
                    },
                ]
            }
        }

        contrib_inventory = {"components": {"receiver": []}}

        result = merge_inventories(core_inventory, contrib_inventory)

        receivers = result["components"]["receiver"]
        assert len(receivers) == 1
        assert receivers[0]["name"] == "otlpreceiver"

    def test_merge_empty_inventories(self):
        """Test merging when one inventory is empty."""
        core_inventory = {"components": {}}
        contrib_inventory = {
            "components": {
                "receiver": [
                    {
                        "name": "zipkinreceiver",
                        "metadata": {},
                    }
                ]
            }
        }

        result = merge_inventories(core_inventory, contrib_inventory)

        assert len(result["components"]["receiver"]) == 1
        assert result["components"]["receiver"][0]["name"] == "zipkinreceiver"

    def test_merge_preserves_source_repo(self):
        """Test that source_repo is correctly set."""
        core_inventory = {
            "components": {
                "receiver": [
                    {
                        "name": "corereceiver",
                        "metadata": {},
                    }
                ]
            }
        }

        contrib_inventory = {
            "components": {
                "receiver": [
                    {
                        "name": "contribreceiver",
                        "metadata": {},
                    }
                ]
            }
        }

        result = merge_inventories(core_inventory, contrib_inventory)

        receivers = result["components"]["receiver"]
        core_rec = next(r for r in receivers if r["name"] == "corereceiver")
        contrib_rec = next(r for r in receivers if r["name"] == "contribreceiver")

        assert core_rec["source_repo"] == "core"
        assert contrib_rec["source_repo"] == "contrib"

    def test_merge_sorts_components(self):
        """Test that merged components are sorted by name."""
        core_inventory = {
            "components": {
                "receiver": [
                    {"name": "zreceiver", "metadata": {}},
                    {"name": "areceiver", "metadata": {}},
                ]
            }
        }

        contrib_inventory = {
            "components": {
                "receiver": [
                    {"name": "mreceiver", "metadata": {}},
                ]
            }
        }

        result = merge_inventories(core_inventory, contrib_inventory)

        receivers = result["components"]["receiver"]
        names = [r["name"] for r in receivers]
        assert names == ["areceiver", "mreceiver", "zreceiver"]
