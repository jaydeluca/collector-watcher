"""Tests for documentation generator."""

from pathlib import Path

import pytest

from collector_watcher.doc_generator import DocGenerator


@pytest.fixture
def doc_generator():
    """Create a DocGenerator instance for testing."""
    return DocGenerator(repository="opentelemetry-collector-contrib")


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

        # Check distribution section
        assert "## Contrib Distribution" in page_content
        assert "Components from the [OpenTelemetry Collector Contrib]" in page_content

        # Check explanation text
        assert (
            "The **Traces**, **Metrics**, and **Logs** columns show the stability level for each signal type."
            in page_content
        )

        # Check table headers (separate columns, no Documentation column)
        assert "| Name | Traces | Metrics | Logs |" in page_content

        # Check components are listed (alphabetically) with separate columns and name as link
        assert (
            "| [jaegerreceiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/jaegerreceiver) | beta | - | - |"
            in page_content
        )
        assert (
            "| [otlpreceiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/otlpreceiver) | beta | beta | beta |"
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

        # Check distribution section
        assert "## Contrib Distribution" in page_content

        # Check explanation text
        assert (
            "The **Stability** column indicates the maturity level of each extension."
            in page_content
        )

        # Extensions should have different stability header (no separate signal columns)
        assert "| Name | Stability |" in page_content

        # Check component with name as link
        assert (
            "| [healthcheckextension](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/extension/healthcheckextension) | beta |"
            in page_content
        )

    def test_generate_component_page_mixed_distributions(self, doc_generator):
        """Test generating a page with both core and contrib components."""
        components = [
            {
                "name": "otlpreceiver",
                "metadata": {
                    "status": {
                        "stability": {"beta": ["traces", "metrics", "logs"]},
                        "distributions": ["core"],
                    }
                },
            },
            {
                "name": "jaegerreceiver",
                "metadata": {
                    "status": {"stability": {"beta": ["traces"]}, "distributions": ["contrib"]}
                },
            },
            {
                "name": "zipkinreceiver",
                "metadata": {
                    "status": {
                        "stability": {"beta": ["traces"]},
                        "distributions": ["core", "contrib"],
                    }
                },
            },
        ]

        page_content = doc_generator.generate_component_page("receiver", components)

        # Check both distribution sections exist
        assert "## Core Distribution" in page_content
        assert "## Contrib Distribution" in page_content
        assert (
            "Components from the [OpenTelemetry Collector](https://github.com/open-telemetry/opentelemetry-collector)"
            in page_content
        )
        assert "Components from the [OpenTelemetry Collector Contrib]" in page_content

        # Core components should link to core repo
        assert (
            "[otlpreceiver](https://github.com/open-telemetry/opentelemetry-collector/tree/main/receiver/otlpreceiver)"
            in page_content
        )
        assert (
            "[zipkinreceiver](https://github.com/open-telemetry/opentelemetry-collector/tree/main/receiver/zipkinreceiver)"
            in page_content
        )

        # Contrib components should link to contrib repo
        assert (
            "[jaegerreceiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/jaegerreceiver)"
            in page_content
        )

    def test_generate_component_page_empty_list(self, doc_generator):
        """Test generating a component page with no components."""
        page_content = doc_generator.generate_component_page("processor", [])

        # Should still have basic structure
        assert "title: Processors" in page_content
        # But no distribution sections since no components
        assert "## Core Distribution" not in page_content
        assert "## Contrib Distribution" not in page_content

    def test_generate_component_page_no_metadata(self, doc_generator):
        """Test generating a component page with components lacking metadata."""
        components = [{"name": "fooprocessor"}]

        page_content = doc_generator.generate_component_page("processor", components)

        # Should have contrib section (default when no metadata)
        assert "## Contrib Distribution" in page_content
        # Should show dashes for all stability columns when no metadata, and name as link
        assert (
            "| [fooprocessor](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/processor/fooprocessor) | - | - | - |"
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


class TestGenerateIndexPage:
    """Tests for generate_index_page function."""

    def test_generate_index_page(self, doc_generator):
        """Test generating the components index page."""
        page_content = doc_generator.generate_index_page()

        # Check Hugo front matter
        assert "---" in page_content
        assert "title: Components" in page_content
        assert "weight: 300" in page_content

        # Check component type links
        assert "[Receivers](receiver/)" in page_content
        assert "[Processors](processor/)" in page_content
        assert "[Exporters](exporter/)" in page_content
        assert "[Connectors](connector/)" in page_content
        assert "[Extensions](extension/)" in page_content

        # Check stability level descriptions
        assert "**stable**" in page_content
        assert "**beta**" in page_content
        assert "**alpha**" in page_content
        assert "**development**" in page_content

        # Check general content
        assert "OpenTelemetry Collector" in page_content


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

        # Should have 6 pages: _index.md + 5 component type pages
        assert len(pages) == 6

        # Check paths
        components_dir = output_dir / "components"
        assert str(components_dir / "_index.md") in pages
        assert str(components_dir / "receiver.md") in pages
        assert str(components_dir / "processor.md") in pages
        assert str(components_dir / "exporter.md") in pages
        assert str(components_dir / "connector.md") in pages
        assert str(components_dir / "extension.md") in pages

        # Check index page content
        index_content = pages[str(components_dir / "_index.md")]
        assert "title: Components" in index_content

        # Check receiver page content (with name as link and distribution section)
        receiver_content = pages[str(components_dir / "receiver.md")]
        assert "## Contrib Distribution" in receiver_content
        assert (
            "| [otlpreceiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/otlpreceiver) | beta | beta | beta |"
            in receiver_content
        )

        # Check extension page content (with name as link and distribution section)
        extension_content = pages[str(components_dir / "extension.md")]
        assert "## Contrib Distribution" in extension_content
        assert (
            "| [healthcheckextension](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/extension/healthcheckextension) | beta |"
            in extension_content
        )

    def test_generate_all_pages_empty_inventory(self, doc_generator):
        """Test generating all pages from empty inventory."""
        inventory = {"repository": "opentelemetry-collector-contrib", "components": {}}

        output_dir = Path("/fake/path/content/en/docs/collector")
        pages = doc_generator.generate_all_pages(inventory, output_dir)

        # Should still generate all 6 pages
        assert len(pages) == 6

        # Pages should exist but have no component rows
        components_dir = output_dir / "components"
        receiver_content = pages[str(components_dir / "receiver.md")]
        assert "title: Receivers" in receiver_content
        # Should have description but no distribution sections when no components
        assert (
            "Receivers collect telemetry data from various sources and formats." in receiver_content
        )
        assert "## Core Distribution" not in receiver_content
        assert "## Contrib Distribution" not in receiver_content
