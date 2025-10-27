"""Tests for documentation generator."""

from pathlib import Path

import pytest

from collector_watcher.doc_generator import DocGenerator


@pytest.fixture
def doc_generator():
    """Create a DocGenerator instance for testing."""
    return DocGenerator(version="v0.138.0")


class TestGetStabilityBySignal:
    """Tests for get_stability_by_signal function."""

    def test_get_stability_single_signal_beta(self, doc_generator):
        """Test getting stability for a single signal (beta)."""
        metadata = {"status": {"stability": {"beta": ["metrics"]}}}
        result = doc_generator.get_stability_by_signal(metadata)
        assert result == {"metrics": "beta"}

    def test_get_stability_multiple_signals_same_level(self, doc_generator):
        """Test getting stability for multiple signals at same level."""
        metadata = {"status": {"stability": {"beta": ["traces", "metrics", "logs"]}}}
        result = doc_generator.get_stability_by_signal(metadata)
        assert result == {"traces": "beta", "metrics": "beta", "logs": "beta"}

    def test_get_stability_multiple_signals_different_levels(self, doc_generator):
        """Test getting stability for multiple signals at different levels."""
        metadata = {"status": {"stability": {"beta": ["traces", "metrics"], "alpha": ["logs"]}}}
        result = doc_generator.get_stability_by_signal(metadata)
        assert result == {"traces": "beta", "metrics": "beta", "logs": "alpha"}

    def test_get_stability_extension(self, doc_generator):
        """Test getting stability for extensions (single signal type)."""
        metadata = {"status": {"stability": {"beta": ["extension"]}}}
        result = doc_generator.get_stability_by_signal(metadata)
        assert result == {"extension": "beta"}

    def test_get_stability_no_metadata(self, doc_generator):
        """Test getting stability when no metadata exists."""
        assert doc_generator.get_stability_by_signal({}) == {}
        assert doc_generator.get_stability_by_signal(None) == {}

    def test_get_stability_no_stability_field(self, doc_generator):
        """Test getting stability when stability field is missing."""
        metadata = {"status": {}}
        assert doc_generator.get_stability_by_signal(metadata) == {}

    def test_get_stability_empty_stability(self, doc_generator):
        """Test getting stability when stability dict is empty."""
        metadata = {"status": {"stability": {}}}
        assert doc_generator.get_stability_by_signal(metadata) == {}

    def test_get_stability_partial_signals(self, doc_generator):
        """Test getting stability with only some signals defined."""
        metadata = {"status": {"stability": {"alpha": ["traces"]}}}
        result = doc_generator.get_stability_by_signal(metadata)
        assert result == {"traces": "alpha"}

    def test_get_stability_development_level(self, doc_generator):
        """Test getting stability with development level."""
        metadata = {"status": {"stability": {"development": ["traces", "logs"]}}}
        result = doc_generator.get_stability_by_signal(metadata)
        assert result == {"traces": "development", "logs": "development"}

    def test_get_stability_unmaintained_level(self, doc_generator):
        """Test getting stability with unmaintained level."""
        metadata = {"status": {"stability": {"unmaintained": ["extension"]}}}
        result = doc_generator.get_stability_by_signal(metadata)
        assert result == {"extension": "unmaintained"}


class TestGenerateComponentPage:
    """Tests for generate_component_page function."""

    def test_generate_component_page_receiver(self, doc_generator):
        """Test generating a receiver component page."""
        components = [
            {
                "name": "otlpreceiver",
                "metadata": {
                    "status": {
                        "stability": {"beta": ["traces", "metrics", "logs"]},
                        "distributions": ["contrib"],
                    }
                },
            },
            {
                "name": "jaegerreceiver",
                "metadata": {
                    "status": {"stability": {"beta": ["traces"]}, "distributions": ["contrib"]}
                },
            },
        ]

        page_content = doc_generator.generate_component_page("receiver", components)

        # Check Hugo front matter
        assert "---" in page_content
        assert "title: Receivers" in page_content
        assert "weight: 310" in page_content

        # Check description
        assert "Receivers collect telemetry data" in page_content

        # Check version info
        assert "_Generated from version v0.138.0_" in page_content

        # Check table headers (now includes Distributions column with footnote references)
        assert "| Name | Distributions[^1] | Traces[^2] | Metrics[^2] | Logs[^2] |" in page_content

        # Check footnote definitions
        assert "[^1]: Shows which distributions" in page_content
        assert "[^2]: For details about component stability levels" in page_content
        assert "component-stability.md" in page_content

        # Check components are listed (alphabetically) with distributions column
        assert (
            "| [jaegerreceiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/jaegerreceiver) | contrib | beta | - | - |"
            in page_content
        )
        assert (
            "| [otlpreceiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/otlpreceiver) | contrib | beta | beta | beta |"
            in page_content
        )

    def test_generate_component_page_extension(self, doc_generator):
        """Test generating an extension component page."""
        components = [
            {
                "name": "healthcheckextension",
                "metadata": {
                    "status": {"stability": {"beta": ["extension"]}, "distributions": ["contrib"]}
                },
            }
        ]

        page_content = doc_generator.generate_component_page("extension", components)

        # Check title
        assert "title: Extensions" in page_content
        assert "weight: 350" in page_content

        # Extensions should have Distributions and Stability columns with footnote references
        assert "| Name | Distributions[^1] | Stability[^2] |" in page_content

        # Check footnote definitions
        assert "[^1]: Shows which distributions" in page_content
        assert "[^2]: For details about component stability levels" in page_content
        assert "component-stability.md" in page_content

        # Check component with distributions column
        assert (
            "| [healthcheckextension](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/extension/healthcheckextension) | contrib | beta |"
            in page_content
        )

    def test_generate_component_page_mixed_distributions(self, doc_generator):
        """Test generating a page with components from different distributions."""
        components = [
            {
                "name": "otlpreceiver",
                "source_repo": "core",  # Component source is in core repo
                "metadata": {
                    "status": {
                        "stability": {"beta": ["traces", "metrics", "logs"]},
                        "distributions": ["core"],
                    }
                },
            },
            {
                "name": "jaegerreceiver",
                "source_repo": "contrib",  # Component source is in contrib repo
                "metadata": {
                    "status": {"stability": {"beta": ["traces"]}, "distributions": ["contrib"]}
                },
            },
            {
                "name": "zipkinreceiver",
                "source_repo": "core",  # Component source is in core repo, but included in both distributions
                "metadata": {
                    "status": {
                        "stability": {"beta": ["traces"]},
                        "distributions": ["contrib", "core"],  # Will be sorted to "contrib, core"
                    }
                },
            },
        ]

        page_content = doc_generator.generate_component_page("receiver", components)

        # Should be a unified table (no separate distribution sections)
        assert "## Core Distribution" not in page_content
        assert "## Contrib Distribution" not in page_content

        # Check table has distributions column with footnote references
        assert "| Name | Distributions[^1] | Traces[^2] | Metrics[^2] | Logs[^2] |" in page_content

        # Core components should show "core" in distributions and link to core repo
        assert (
            "[otlpreceiver](https://github.com/open-telemetry/opentelemetry-collector/tree/main/receiver/otlpreceiver) | core |"
            in page_content
        )

        # Contrib-only components should show "contrib" and link to contrib repo
        assert (
            "[jaegerreceiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/jaegerreceiver) | contrib |"
            in page_content
        )

        # Multi-distribution components should show both (sorted) and link to core repo (priority)
        assert (
            "[zipkinreceiver](https://github.com/open-telemetry/opentelemetry-collector/tree/main/receiver/zipkinreceiver) | contrib, core |"
            in page_content
        )

    def test_generate_component_page_empty_list(self, doc_generator):
        """Test generating a component page with no components."""
        page_content = doc_generator.generate_component_page("processor", [])

        # Should still have basic structure
        assert "title: Processors" in page_content
        # Should have description and table headers even with no components
        assert "Processors transform, filter" in page_content

    def test_generate_component_page_no_metadata(self, doc_generator):
        """Test generating a component page with components lacking metadata."""
        components = [{"name": "fooprocessor"}]

        page_content = doc_generator.generate_component_page("processor", components)

        # Should default to "contrib" distribution and show dashes for stability
        assert (
            "| [fooprocessor](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/processor/fooprocessor) | contrib | - | - | - |"
            in page_content
        )

    def test_generate_component_page_sorting(self, doc_generator):
        """Test that components are sorted alphabetically."""
        components = [
            {
                "name": "zreceiver",
                "metadata": {
                    "status": {"stability": {"beta": ["traces"]}, "distributions": ["contrib"]}
                },
            },
            {
                "name": "areceiver",
                "metadata": {
                    "status": {"stability": {"alpha": ["metrics"]}, "distributions": ["contrib"]}
                },
            },
            {
                "name": "mreceiver",
                "metadata": {
                    "status": {"stability": {"beta": ["logs"]}, "distributions": ["contrib"]}
                },
            },
        ]

        page_content = doc_generator.generate_component_page("receiver", components)

        # Find positions in the content (component names are now links)
        a_pos = page_content.find("| [areceiver]")
        m_pos = page_content.find("| [mreceiver]")
        z_pos = page_content.find("| [zreceiver]")

        # Verify alphabetical order
        assert a_pos < m_pos < z_pos


class TestGenerateAllPages:
    """Tests for generate_all_pages function."""

    def test_generate_all_pages(self, doc_generator):
        """Test generating all pages from inventory."""
        inventory = {
            "repository": "opentelemetry-collector-contrib",
            "components": {
                "receiver": [
                    {
                        "name": "otlpreceiver",
                        "metadata": {
                            "status": {
                                "stability": {"beta": ["traces", "metrics", "logs"]},
                                "distributions": ["contrib"],
                            }
                        },
                    }
                ],
                "processor": [
                    {
                        "name": "batchprocessor",
                        "metadata": {
                            "status": {
                                "stability": {"beta": ["traces", "metrics", "logs"]},
                                "distributions": ["contrib"],
                            }
                        },
                    }
                ],
                "exporter": [],
                "connector": [],
                "extension": [
                    {
                        "name": "healthcheckextension",
                        "metadata": {
                            "status": {
                                "stability": {"beta": ["extension"]},
                                "distributions": ["contrib"],
                            }
                        },
                    }
                ],
            },
        }

        output_dir = Path("/fake/path/content/en/docs/collector")
        pages = doc_generator.generate_all_pages(inventory, output_dir)

        # Should have 5 pages: 5 component type pages (no index for marker-based approach)
        assert len(pages) == 5

        # Check paths
        components_dir = output_dir / "components"
        assert str(components_dir / "receiver.md") in pages
        assert str(components_dir / "processor.md") in pages
        assert str(components_dir / "exporter.md") in pages
        assert str(components_dir / "connector.md") in pages
        assert str(components_dir / "extension.md") in pages

        # Check receiver page content (with distributions column)
        receiver_content = pages[str(components_dir / "receiver.md")]
        assert (
            "| [otlpreceiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/otlpreceiver) | contrib | beta | beta | beta |"
            in receiver_content
        )

        # Check extension page content (with distributions column)
        extension_content = pages[str(components_dir / "extension.md")]
        assert (
            "| [healthcheckextension](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/extension/healthcheckextension) | contrib | beta |"
            in extension_content
        )

    def test_generate_all_pages_empty_inventory(self, doc_generator):
        """Test generating all pages from empty inventory."""
        inventory = {"repository": "opentelemetry-collector-contrib", "components": {}}

        output_dir = Path("/fake/path/content/en/docs/collector")
        pages = doc_generator.generate_all_pages(inventory, output_dir)

        # Should still generate all 5 component pages (no index for marker-based approach)
        assert len(pages) == 5

        # Pages should exist but have no component rows
        components_dir = output_dir / "components"
        receiver_content = pages[str(components_dir / "receiver.md")]
        assert "title: Receivers" in receiver_content
        # Should have description
        assert (
            "Receivers collect telemetry data from various sources and formats." in receiver_content
        )
