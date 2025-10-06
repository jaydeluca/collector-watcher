"""Documentation generator for OpenTelemetry Collector components."""

from pathlib import Path
from typing import Any


class DocGenerator:
    """Generates Hugo markdown documentation pages from component inventory."""

    # Component type descriptions
    COMPONENT_DESCRIPTIONS = {
        "receiver": "Receivers collect telemetry data from various sources and formats.",
        "processor": "Processors transform, filter, and enrich telemetry data as it flows through the pipeline.",
        "exporter": "Exporters send telemetry data to observability backends and destinations.",
        "connector": "Connectors connect two pipelines, acting as both exporter and receiver.",
        "extension": "Extensions provide additional capabilities like health checks and service discovery.",
    }

    # Weight for Hugo front matter (determines page ordering)
    COMPONENT_WEIGHTS = {
        "receiver": 310,
        "processor": 320,
        "exporter": 330,
        "connector": 340,
        "extension": 350,
    }

    def __init__(self, repository: str = "opentelemetry-collector-contrib"):
        """
        Initialize the documentation generator.

        Args:
            repository: Name of the repository (used for GitHub links)
        """
        self.repository = repository

    def get_stability_by_signal(self, metadata: dict[str, Any]) -> dict[str, str]:
        """
        Get stability information by signal type.

        Args:
            metadata: Component metadata containing status.stability

        Returns:
            Dictionary mapping signal type to stability level
            For extensions: {"extension": "beta"}
            For others: {"traces": "beta", "metrics": "alpha", "logs": "-"}
        """
        if not metadata or "status" not in metadata:
            return {}

        status = metadata.get("status", {})
        stability = status.get("stability", {})

        if not stability:
            return {}

        # Build a map of signal -> stability level
        signal_stability = {}
        for level, signals in stability.items():
            if isinstance(signals, list):
                for signal in signals:
                    signal_stability[signal] = level

        return signal_stability

    def _get_distribution(self, component: dict[str, Any]) -> str:
        """
        Get the primary distribution for a component.

        Args:
            component: Component data

        Returns:
            Distribution name ("core" or "contrib")
        """
        metadata = component.get("metadata", {})
        if not metadata:
            # Default to contrib if no metadata
            return "contrib"

        status = metadata.get("status", {})
        distributions = status.get("distributions", [])

        # Priority: core > contrib > other
        if "core" in distributions:
            return "core"
        elif "contrib" in distributions:
            return "contrib"
        elif distributions:
            # If has other distributions (like k8s), default to contrib
            return "contrib"
        else:
            # No distribution specified, default to contrib
            return "contrib"

    def generate_component_page(self, component_type: str, components: list[dict[str, Any]]) -> str:
        """
        Generate a Hugo markdown page for a component type.

        Args:
            component_type: Type of component (receiver, processor, etc.)
            components: List of components of this type

        Returns:
            Markdown content for the page
        """
        # Capitalize component type for title
        title = component_type.capitalize() + "s"
        description = self.COMPONENT_DESCRIPTIONS.get(
            component_type, f"List of available OpenTelemetry Collector {component_type}s"
        )
        weight = self.COMPONENT_WEIGHTS.get(component_type, 300)

        # Hugo front matter
        front_matter = f"""---
title: {title}
description: List of available OpenTelemetry Collector {component_type}s
weight: {weight}
---

"""

        # Component description
        content = front_matter
        content += f"{description}\n\n"

        # Group components by distribution
        core_components = []
        contrib_components = []

        for component in components:
            distribution = self._get_distribution(component)
            if distribution == "core":
                core_components.append(component)
            else:
                contrib_components.append(component)

        # Sort components alphabetically by name within each distribution
        core_components.sort(key=lambda c: c.get("name", ""))
        contrib_components.sort(key=lambda c: c.get("name", ""))

        # Generate Core Distribution section
        if core_components:
            content += "## Core Distribution\n\n"
            content += "Components from the [OpenTelemetry Collector](https://github.com/open-telemetry/opentelemetry-collector) core distribution.\n\n"
            content += self._generate_component_table(component_type, core_components)
            content += "\n"

        # Generate Contrib Distribution section
        if contrib_components:
            content += "## Contrib Distribution\n\n"
            content += "Components from the [OpenTelemetry Collector Contrib](https://github.com/open-telemetry/opentelemetry-collector-contrib) distribution.\n\n"
            content += self._generate_component_table(component_type, contrib_components)

        return content

    def _generate_component_table(
        self, component_type: str, components: list[dict[str, Any]]
    ) -> str:
        """
        Generate a table of components.

        Args:
            component_type: Type of component (receiver, processor, etc.)
            components: List of components to include in table

        Returns:
            Markdown table content
        """
        table_content = ""

        # Add column explanation
        if component_type == "extension":
            table_content += (
                "The **Stability** column indicates the maturity level of each extension.\n\n"
            )
            table_content += "| Name | Stability |\n"
            table_content += "|------|----------|\n"
        else:
            table_content += "The **Traces**, **Metrics**, and **Logs** columns show the stability level for each signal type.\n\n"
            table_content += "| Name | Traces | Metrics | Logs |\n"
            table_content += "|------|--------|---------|------|\n"

        # Table rows
        for component in components:
            name = component.get("name", "unknown")
            metadata = component.get("metadata", {})

            # Get stability by signal
            stability_map = self.get_stability_by_signal(metadata)

            # Generate GitHub link
            # Determine which repository this component is from
            distribution = self._get_distribution(component)
            if distribution == "core":
                repo_name = "opentelemetry-collector"
            else:
                repo_name = "opentelemetry-collector-contrib"

            repo_url = f"https://github.com/open-telemetry/{repo_name}"
            component_path = f"{component_type}/{name}"
            readme_link = f"{repo_url}/tree/main/{component_path}"

            # Make component name a link
            name_link = f"[{name}]({readme_link})"

            if component_type == "extension":
                # Single stability column for extensions
                stability = stability_map.get("extension", "N/A")
                table_content += f"| {name_link} | {stability} |\n"
            else:
                # Separate columns for traces/metrics/logs
                traces = stability_map.get("traces", "-")
                metrics = stability_map.get("metrics", "-")
                logs = stability_map.get("logs", "-")
                table_content += f"| {name_link} | {traces} | {metrics} | {logs} |\n"

        return table_content

    def generate_index_page(self) -> str:
        """
        Generate the components/_index.md landing page.

        Returns:
            Markdown content for the index page
        """
        content = """---
title: Components
description: OpenTelemetry Collector components - receivers, processors, exporters, connectors, and extensions
weight: 300
---

The OpenTelemetry Collector is made up of components that handle telemetry data. Each component has a specific role in the data pipeline.

## Component Types

- **[Receivers](receiver/)** - Collect telemetry data from various sources and formats
- **[Processors](processor/)** - Transform, filter, and enrich telemetry data
- **[Exporters](exporter/)** - Send telemetry data to observability backends
- **[Connectors](connector/)** - Connect two pipelines, acting as both exporter and receiver
- **[Extensions](extension/)** - Provide additional capabilities like health checks

## Stability Levels

Each component has a stability level that indicates its maturity:

- **stable** - Ready for production use
- **beta** - Mostly stable, but may have minor changes
- **alpha** - Early development, expect breaking changes
- **development** - Experimental, not recommended for production
- **unmaintained** - No longer actively maintained

For signal-based components (receivers, processors, exporters, connectors), stability is shown per signal type (traces/metrics/logs).

## Contributing

To learn more about developing Collector components, see the [Collector development documentation](https://github.com/open-telemetry/opentelemetry-collector/blob/main/CONTRIBUTING.md).
"""
        return content

    def generate_all_pages(
        self, inventory: dict[str, Any], output_dir: str | Path
    ) -> dict[str, str]:
        """
        Generate all component pages from inventory.

        Args:
            inventory: Complete inventory data
            output_dir: Base directory for output (e.g., content/en/docs/collector)

        Returns:
            Dictionary mapping file paths to content
        """
        output_dir = Path(output_dir)
        components_dir = output_dir / "components"

        pages = {}

        # Generate index page
        index_path = str(components_dir / "_index.md")
        pages[index_path] = self.generate_index_page()

        # Generate page for each component type
        components = inventory.get("components", {})
        for component_type in ["receiver", "processor", "exporter", "connector", "extension"]:
            component_list = components.get(component_type, [])
            page_path = str(components_dir / f"{component_type}.md")
            pages[page_path] = self.generate_component_page(component_type, component_list)

        return pages
