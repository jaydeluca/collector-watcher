"""Tests for documentation generator."""

import pytest

from docs_automation.doc_generator import DocGenerator


@pytest.fixture
def doc_generator():
    """Create a DocGenerator instance for testing."""
    return DocGenerator(version="v0.138.0")


class TestGetStabilityBySignal:
    """Tests for get_stability_by_signal function."""

    def test_get_stability_single_signal_beta(self, doc_generator):
        metadata = {"status": {"stability": {"beta": ["metrics"]}}}
        result = doc_generator.get_stability_by_signal(metadata)
        assert result == {"metrics": "beta"}

    def test_get_stability_multiple_signals_same_level(self, doc_generator):
        metadata = {"status": {"stability": {"beta": ["traces", "metrics", "logs"]}}}
        result = doc_generator.get_stability_by_signal(metadata)
        assert result == {"traces": "beta", "metrics": "beta", "logs": "beta"}

    def test_get_stability_multiple_signals_different_levels(self, doc_generator):
        metadata = {"status": {"stability": {"beta": ["traces", "metrics"], "alpha": ["logs"]}}}
        result = doc_generator.get_stability_by_signal(metadata)
        assert result == {"traces": "beta", "metrics": "beta", "logs": "alpha"}

    def test_get_stability_extension(self, doc_generator):
        metadata = {"status": {"stability": {"beta": ["extension"]}}}
        result = doc_generator.get_stability_by_signal(metadata)
        assert result == {"extension": "beta"}

    def test_get_stability_no_metadata(self, doc_generator):
        assert doc_generator.get_stability_by_signal({}) == {}
        assert doc_generator.get_stability_by_signal(None) == {}

    def test_get_stability_no_stability_field(self, doc_generator):
        metadata = {"status": {}}
        assert doc_generator.get_stability_by_signal(metadata) == {}

    def test_get_stability_empty_stability(self, doc_generator):
        metadata = {"status": {"stability": {}}}
        assert doc_generator.get_stability_by_signal(metadata) == {}

    def test_get_stability_partial_signals(self, doc_generator):
        metadata = {"status": {"stability": {"alpha": ["traces"]}}}
        result = doc_generator.get_stability_by_signal(metadata)
        assert result == {"traces": "alpha"}

    def test_get_stability_development_level(self, doc_generator):
        metadata = {"status": {"stability": {"development": ["traces", "logs"]}}}
        result = doc_generator.get_stability_by_signal(metadata)
        assert result == {"traces": "development", "logs": "development"}

    def test_get_stability_unmaintained_level(self, doc_generator):
        metadata = {"status": {"stability": {"unmaintained": ["extension"]}}}
        result = doc_generator.get_stability_by_signal(metadata)
        assert result == {"extension": "unmaintained"}


class TestIsUnmaintained:
    """Tests for _is_unmaintained method."""

    def test_is_unmaintained_with_unmaintained_stability(self, doc_generator):
        """Test component with unmaintained stability level is unmaintained."""
        component = {
            "name": "oldreceiver",
            "metadata": {"status": {"stability": {"unmaintained": ["metrics"]}}},
        }
        assert doc_generator._is_unmaintained(component) is True

    def test_is_unmaintained_with_normal_stability(self, doc_generator):
        """Test component with normal stability levels is not unmaintained."""
        component = {
            "name": "activereceiver",
            "metadata": {"status": {"stability": {"beta": ["traces", "metrics"]}}},
        }
        assert doc_generator._is_unmaintained(component) is False

    def test_is_unmaintained_no_stability_field(self, doc_generator):
        """Test component without stability field is not considered unmaintained."""
        component = {
            "name": "somereceiver",
            "metadata": {"status": {}},
        }
        assert doc_generator._is_unmaintained(component) is False

    def test_is_unmaintained_no_metadata(self, doc_generator):
        """Test component without metadata is not considered unmaintained."""
        component = {"name": "somereceiver"}
        assert doc_generator._is_unmaintained(component) is False

    def test_is_unmaintained_multiple_stability_levels(self, doc_generator):
        """Test component with unmaintained among other levels is unmaintained."""
        component = {
            "name": "oldreceiver",
            "metadata": {
                "status": {
                    "stability": {
                        "beta": ["traces"],
                        "unmaintained": ["metrics"],
                    }
                }
            },
        }
        assert doc_generator._is_unmaintained(component) is True


class TestGenerateComponentTable:
    """Tests for generate_component_table function (marker-based approach)."""

    def test_generate_component_table_receiver(self, doc_generator):
        """Test generating a receiver table with traces/metrics/logs columns."""
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
                    "status": {
                        "stability": {"beta": ["traces"]},
                        "distributions": ["contrib"],
                    }
                },
            },
        ]

        table_content = doc_generator.generate_component_table("receiver", components)

        assert "| Name | Distributions[^1] | Traces[^2] | Metrics[^2] | Logs[^2] |" in table_content
        assert "[^1]: Shows which distributions" in table_content
        assert "[^2]: For details about component stability levels" in table_content
        assert "component-stability.md" in table_content

        assert (
            "| [jaegerreceiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/jaegerreceiver) | contrib | beta | - | - |"
            in table_content
        )
        assert (
            "| [otlpreceiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/otlpreceiver) | contrib | beta | beta | beta |"
            in table_content
        )

    def test_generate_component_table_extension(self, doc_generator):
        """Test generating an extension table with single stability column."""
        components = [
            {
                "name": "healthcheckextension",
                "metadata": {
                    "status": {"stability": {"beta": ["extension"]}, "distributions": ["contrib"]}
                },
            }
        ]

        table_content = doc_generator.generate_component_table("extension", components)

        assert "| Name | Distributions[^1] | Stability[^2] |" in table_content
        assert "[^1]: Shows which distributions" in table_content
        assert "[^2]: For details about component stability levels" in table_content

        assert (
            "| [healthcheckextension](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/extension/healthcheckextension) | contrib | beta |"
            in table_content
        )

    def test_generate_component_table_with_distributions(self, doc_generator):
        """Test that distributions column shows correct values."""
        components = [
            {
                "name": "otlpreceiver",
                "source_repo": "core",
                "metadata": {
                    "status": {
                        "stability": {"beta": ["traces", "metrics", "logs"]},
                        "distributions": ["core"],
                    }
                },
            },
            {
                "name": "jaegerreceiver",
                "source_repo": "contrib",
                "metadata": {
                    "status": {"stability": {"beta": ["traces"]}, "distributions": ["contrib"]}
                },
            },
            {
                "name": "zipkinreceiver",
                "source_repo": "core",
                "metadata": {
                    "status": {
                        "stability": {"beta": ["traces"]},
                        "distributions": ["contrib", "core"],
                    }
                },
            },
        ]

        table_content = doc_generator.generate_component_table("receiver", components)

        assert (
            "[otlpreceiver](https://github.com/open-telemetry/opentelemetry-collector/tree/main/receiver/otlpreceiver) | core |"
            in table_content
        )
        assert (
            "[jaegerreceiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/jaegerreceiver) | contrib |"
            in table_content
        )
        assert (
            "[zipkinreceiver](https://github.com/open-telemetry/opentelemetry-collector/tree/main/receiver/zipkinreceiver) | contrib, core |"
            in table_content
        )

    def test_generate_component_table_sorting(self, doc_generator):
        """Test components are sorted alphabetically."""
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

        table_content = doc_generator.generate_component_table("receiver", components)

        a_pos = table_content.find("| [areceiver]")
        m_pos = table_content.find("| [mreceiver]")
        z_pos = table_content.find("| [zreceiver]")

        # Verify alphabetical order
        assert a_pos < m_pos < z_pos

    def test_generate_component_table_no_metadata(self, doc_generator):
        """Test handling of components without metadata."""
        components = [{"name": "fooprocessor"}]

        table_content = doc_generator.generate_component_table("processor", components)

        assert (
            "| [fooprocessor](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/processor/fooprocessor) | contrib | - | - | - |"
            in table_content
        )

    def test_generate_component_table_empty_list(self, doc_generator):
        """Test generating table with empty component list."""
        table_content = doc_generator.generate_component_table("processor", [])

        # Should still have table structure
        assert "| Name | Distributions[^1] | Traces[^2] | Metrics[^2] | Logs[^2] |" in table_content
        assert "[^1]: Shows which distributions" in table_content

        # But no component rows (only headers)
        lines = table_content.strip().split("\n")
        # Should have: header, separator, footnotes - no data rows
        assert (
            len(
                [
                    line
                    for line in lines
                    if line.startswith("|") and "[" in line and "Name" not in line
                ]
            )
            == 0
        )

    def test_generate_component_table_unmaintained_component(self, doc_generator):
        """Test that unmaintained components get a warning emoji."""
        components = [
            {
                "name": "oldreceiver",
                "metadata": {
                    "status": {
                        "stability": {"unmaintained": ["metrics"]},
                        "distributions": ["contrib"],
                    }
                },
            },
            {
                "name": "activereceiver",
                "metadata": {
                    "status": {
                        "stability": {"beta": ["traces"]},
                        "distributions": ["contrib"],
                    }
                },
            },
        ]

        table_content = doc_generator.generate_component_table("receiver", components)

        # Unmaintained component should have emoji
        assert "[oldreceiver]" in table_content
        assert "oldreceiver) ⚠️" in table_content

        # Active component should not have emoji
        assert "[activereceiver]" in table_content
        assert "activereceiver) ⚠️" not in table_content

        # Should have note about unmaintained components
        assert "⚠️ **Note:** Components marked with ⚠️ are unmaintained" in table_content

    def test_generate_component_table_unmaintained_extension(self, doc_generator):
        """Test that unmaintained extensions also get warning emoji."""
        components = [
            {
                "name": "oldextension",
                "metadata": {
                    "status": {
                        "stability": {"unmaintained": ["extension"]},
                        "distributions": ["contrib"],
                    }
                },
            }
        ]

        table_content = doc_generator.generate_component_table("extension", components)

        # Should have emoji
        assert "oldextension) ⚠️" in table_content
        # Should have note
        assert "⚠️ **Note:**" in table_content


class TestGenerateAllComponentTables:
    """Tests for generate_all_component_tables function."""

    def test_generate_all_component_tables(self, doc_generator):
        """Test generating all component type tables."""
        inventory = {
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
            }
        }

        tables = doc_generator.generate_all_component_tables(inventory)

        # Should return dict with all component types
        assert len(tables) == 5
        assert "receiver" in tables
        assert "processor" in tables
        assert "exporter" in tables
        assert "connector" in tables
        assert "extension" in tables

        # Check receiver table content
        receiver_table = tables["receiver"]
        assert (
            "| Name | Distributions[^1] | Traces[^2] | Metrics[^2] | Logs[^2] |" in receiver_table
        )
        assert (
            "| [otlpreceiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/otlpreceiver) | contrib | beta | beta | beta |"
            in receiver_table
        )

        # Check extension table content
        extension_table = tables["extension"]
        assert "| Name | Distributions[^1] | Stability[^2] |" in extension_table
        assert (
            "| [healthcheckextension](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/extension/healthcheckextension) | contrib | beta |"
            in extension_table
        )

    def test_generate_all_component_tables_empty_inventory(self, doc_generator):
        """Test with empty inventory."""
        inventory = {"components": {}}

        tables = doc_generator.generate_all_component_tables(inventory)

        # Should still return all component types with empty tables
        assert len(tables) == 5
        assert "receiver" in tables
        assert "processor" in tables
        assert "exporter" in tables
        assert "connector" in tables
        assert "extension" in tables

        # Each table should have structure but no components
        for _component_type, table in tables.items():
            assert "| Name |" in table
            assert "[^1]:" in table
            assert "[^2]:" in table
