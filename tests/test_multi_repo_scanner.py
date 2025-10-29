"""Tests for multi-repository scanner."""

from unittest.mock import MagicMock, patch

import pytest

from collector_watcher.multi_repo_scanner import MultiRepoScanner


@pytest.fixture
def mock_core_components():
    """Mock component data from core repo."""
    return {
        "processor": [
            {
                "name": "batchprocessor",
                "metadata": {
                    "status": {
                        "stability": {"beta": ["traces", "metrics", "logs"]},
                        "distributions": ["core"],
                    }
                },
            },
            {
                "name": "attributesprocessor",
                "metadata": {
                    "status": {
                        "stability": {"beta": ["traces", "metrics", "logs"]},
                        "distributions": ["core"],
                    }
                },
            },
        ],
        "exporter": [
            {
                "name": "otlpexporter",
                "metadata": {
                    "status": {
                        "stability": {"stable": ["traces", "metrics", "logs"]},
                        "distributions": ["core"],
                    }
                },
            }
        ],
    }


@pytest.fixture
def mock_contrib_components():
    """Mock component data from contrib repo."""
    return {
        "processor": [
            {
                "name": "batchprocessor",
                "metadata": {
                    "status": {
                        "stability": {"beta": ["traces", "metrics", "logs"]},
                        "distributions": ["contrib"],
                        "extra_field": "extra_data",  # Contrib has more metadata
                    }
                },
            },
            {
                "name": "k8sattributesprocessor",
                "metadata": {
                    "status": {
                        "stability": {"beta": ["traces", "metrics", "logs"]},
                        "distributions": ["contrib"],
                    }
                },
            },
        ],
        "exporter": [
            {
                "name": "prometheusexporter",
                "metadata": {
                    "status": {"stability": {"beta": ["metrics"]}, "distributions": ["contrib"]}
                },
            }
        ],
    }


class TestMultiRepoScanner:
    """Tests for MultiRepoScanner class."""

    @patch("collector_watcher.multi_repo_scanner.ComponentScanner")
    def test_scan_all_repos(
        self, mock_scanner_class, mock_core_components, mock_contrib_components
    ):
        """Test scanning all repositories."""
        # Setup mocks
        mock_core_scanner = MagicMock()
        mock_core_scanner.scan_all_components.return_value = mock_core_components

        mock_contrib_scanner = MagicMock()
        mock_contrib_scanner.scan_all_components.return_value = mock_contrib_components

        mock_scanner_class.side_effect = [mock_core_scanner, mock_contrib_scanner]

        # Create scanner
        repos = {"core": "/path/to/core", "contrib": "/path/to/contrib"}
        scanner = MultiRepoScanner(repos)

        # Scan all repos
        result = scanner.scan_all_repos()

        # Verify both scanners were called
        mock_core_scanner.scan_all_components.assert_called_once()
        mock_contrib_scanner.scan_all_components.assert_called_once()

        # Verify result structure
        assert "repository" in result
        assert "components" in result
        assert "processor" in result["components"]
        assert "exporter" in result["components"]

    @patch("collector_watcher.multi_repo_scanner.ComponentScanner")
    def test_merge_component_in_both_repos(
        self, mock_scanner_class, mock_core_components, mock_contrib_components
    ):
        """Test merging a component that exists in both repos."""
        scanner = MultiRepoScanner({"core": "/fake/core", "contrib": "/fake/contrib"})

        inventories = {"core": mock_core_components, "contrib": mock_contrib_components}

        result = scanner._merge_inventories(inventories)

        # Find batchprocessor (exists in both)
        processors = result["components"]["processor"]
        batch = next(p for p in processors if p["name"] == "batchprocessor")

        # Should have both distributions
        assert set(batch["metadata"]["status"]["distributions"]) == {"core", "contrib"}

        # Should prefer contrib metadata (has extra_field)
        assert "extra_field" in batch["metadata"]["status"]
        assert batch["metadata"]["status"]["extra_field"] == "extra_data"

    @patch("collector_watcher.multi_repo_scanner.ComponentScanner")
    def test_merge_component_only_in_core(
        self, mock_scanner_class, mock_core_components, mock_contrib_components
    ):
        """Test component that only exists in core repo."""
        scanner = MultiRepoScanner({"core": "/fake/core", "contrib": "/fake/contrib"})

        inventories = {"core": mock_core_components, "contrib": mock_contrib_components}

        result = scanner._merge_inventories(inventories)

        # Find attributesprocessor (only in core)
        processors = result["components"]["processor"]
        attrs = next(p for p in processors if p["name"] == "attributesprocessor")

        # Should only have core distribution
        assert attrs["metadata"]["status"]["distributions"] == ["core"]

    @patch("collector_watcher.multi_repo_scanner.ComponentScanner")
    def test_merge_component_only_in_contrib(
        self, mock_scanner_class, mock_core_components, mock_contrib_components
    ):
        """Test component that only exists in contrib repo."""
        scanner = MultiRepoScanner({"core": "/fake/core", "contrib": "/fake/contrib"})

        inventories = {"core": mock_core_components, "contrib": mock_contrib_components}

        result = scanner._merge_inventories(inventories)

        # Find k8sattributesprocessor (only in contrib)
        processors = result["components"]["processor"]
        k8s = next(p for p in processors if p["name"] == "k8sattributesprocessor")

        # Should only have contrib distribution
        assert k8s["metadata"]["status"]["distributions"] == ["contrib"]

    @patch("collector_watcher.multi_repo_scanner.ComponentScanner")
    def test_merge_multiple_component_types(
        self, mock_scanner_class, mock_core_components, mock_contrib_components
    ):
        """Test merging multiple component types."""
        scanner = MultiRepoScanner({"core": "/fake/core", "contrib": "/fake/contrib"})

        inventories = {"core": mock_core_components, "contrib": mock_contrib_components}

        result = scanner._merge_inventories(inventories)

        # Should have both processors and exporters
        assert len(result["components"]["processor"]) == 3  # batch, attributes, k8sattributes
        assert len(result["components"]["exporter"]) == 2  # otlp, prometheus

    @patch("collector_watcher.multi_repo_scanner.ComponentScanner")
    def test_merge_sorts_components_alphabetically(
        self, mock_scanner_class, mock_core_components, mock_contrib_components
    ):
        """Test that merged components are sorted alphabetically."""
        scanner = MultiRepoScanner({"core": "/fake/core", "contrib": "/fake/contrib"})

        inventories = {"core": mock_core_components, "contrib": mock_contrib_components}

        result = scanner._merge_inventories(inventories)

        # Processors should be alphabetically sorted
        processors = result["components"]["processor"]
        names = [p["name"] for p in processors]
        assert names == sorted(names)

    @patch("collector_watcher.multi_repo_scanner.ComponentScanner")
    def test_merge_empty_inventories(self, mock_scanner_class):
        """Test merging when inventories are empty."""
        scanner = MultiRepoScanner({"core": "/fake/core", "contrib": "/fake/contrib"})

        inventories = {"core": {}, "contrib": {}}

        result = scanner._merge_inventories(inventories)

        # Should have empty component lists
        for component_type in ["receiver", "processor", "exporter", "connector", "extension"]:
            assert result["components"][component_type] == []

    @patch("collector_watcher.multi_repo_scanner.ComponentScanner")
    def test_merge_component_without_metadata(self, mock_scanner_class):
        """Test merging component without metadata."""
        scanner = MultiRepoScanner({"core": "/fake/core", "contrib": "/fake/contrib"})

        inventories = {
            "core": {
                "processor": [
                    {"name": "testprocessor"}  # No metadata
                ]
            },
            "contrib": {},
        }

        result = scanner._merge_inventories(inventories)

        # Should still work and add distributions
        processors = result["components"]["processor"]
        assert len(processors) == 1
        assert processors[0]["name"] == "testprocessor"
        assert processors[0]["metadata"]["status"]["distributions"] == ["core"]

    @patch("collector_watcher.multi_repo_scanner.ComponentScanner")
    def test_merge_distributions_are_sorted(self, mock_scanner_class):
        """Test that distributions are sorted alphabetically."""
        scanner = MultiRepoScanner({"core": "/fake/core", "contrib": "/fake/contrib"})

        # Create component in both repos (reverse order to test sorting)
        inventories = {
            "contrib": {"processor": [{"name": "test", "metadata": {"status": {}}}]},
            "core": {"processor": [{"name": "test", "metadata": {"status": {}}}]},
        }

        result = scanner._merge_inventories(inventories)

        processors = result["components"]["processor"]
        # Distributions should be sorted: ["contrib", "core"] → ["contrib", "core"]
        # Actually should be ["core", "contrib"] alphabetically
        assert processors[0]["metadata"]["status"]["distributions"] == ["contrib", "core"]
