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

    def __init__(self, version: str | None = None):
        """
        Initialize the documentation generator.

        Args:
            version: Version string to include in generated content (e.g., "v0.138.0")
        """
        self.version = version

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

    def _get_distributions(self, component: dict[str, Any]) -> list[str]:
        """
        Get the list of distributions for a component.

        Args:
            component: Component data

        Returns:
            List of distribution names (e.g., ["core", "contrib"])
        """
        metadata = component.get("metadata", {})
        if not metadata:
            return ["contrib"]

        status = metadata.get("status", {})
        distributions = status.get("distributions", [])

        if not distributions:
            return ["contrib"]

        return sorted(distributions)

    def _format_distributions(self, distributions: list[str]) -> str:
        """
        Format distribution list for display in table.

        Args:
            distributions: List of distribution names

        Returns:
            Formatted string (e.g., "core, contrib")
        """
        if not distributions:
            return "-"

        return ", ".join(distributions)

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

        # Add version info if available
        if self.version:
            content += f"_Generated from version {self.version}_\n\n"

        # Sort components alphabetically by name
        sorted_components = sorted(components, key=lambda c: c.get("name", ""))

        # Generate unified table with distributions column
        content += self._generate_component_table(component_type, sorted_components)

        return content

    def _generate_component_table(
        self, component_type: str, components: list[dict[str, Any]]
    ) -> str:
        """
        Generate a table of components with distributions column.

        Args:
            component_type: Type of component (receiver, processor, etc.)
            components: List of components to include in table

        Returns:
            Markdown table content
        """
        table_content = ""

        # Add table headers with footnote references
        if component_type == "extension":
            table_content += "| Name | Distributions[^1] | Stability[^2] |\n"
            table_content += "|------|-------------------|---------------|\n"
        else:
            table_content += "| Name | Distributions[^1] | Traces[^2] | Metrics[^2] | Logs[^2] |\n"
            table_content += "|------|-------------------|------------|-------------|----------|\n"

        # Table rows
        for component in components:
            name = component.get("name", "unknown")
            metadata = component.get("metadata", {})

            # Get distributions
            distributions = self._get_distributions(component)
            distributions_str = self._format_distributions(distributions)

            # Get stability by signal
            stability_map = self.get_stability_by_signal(metadata)

            # Generate GitHub link based on source repository
            # Use source_repo field if available, otherwise infer from distributions
            source_repo = component.get("source_repo", "contrib")
            
            if source_repo == "core":
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
                table_content += f"| {name_link} | {distributions_str} | {stability} |\n"
            else:
                # Separate columns for traces/metrics/logs
                traces = stability_map.get("traces", "-")
                metrics = stability_map.get("metrics", "-")
                logs = stability_map.get("logs", "-")
                table_content += f"| {name_link} | {distributions_str} | {traces} | {metrics} | {logs} |\n"

        # Add footnotes
        table_content += "\n"
        stability_link = "https://github.com/open-telemetry/opentelemetry-collector/blob/main/docs/component-stability.md"
        
        table_content += (
            "[^1]: Shows which distributions (core, contrib, k8s, etc.) include this component.\n"
            f"[^2]: For details about component stability levels, see the [OpenTelemetry Collector component stability definitions]({stability_link}).\n"
        )

        return table_content

    def generate_table_only(self, component_type: str, components: list[dict[str, Any]]) -> str:
        """
        Generate only the table content for a component type (for marker-based updates).

        Args:
            component_type: Type of component (receiver, processor, etc.)
            components: List of components of this type

        Returns:
            Markdown table content only (no front matter or headers)
        """
        # Sort components alphabetically by name
        sorted_components = sorted(components, key=lambda c: c.get("name", ""))

        # Generate table
        return self._generate_component_table(component_type, sorted_components)

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

        # Generate page for each component type
        components = inventory.get("components", {})
        for component_type in ["receiver", "processor", "exporter", "connector", "extension"]:
            component_list = components.get(component_type, [])
            page_path = str(components_dir / f"{component_type}.md")
            pages[page_path] = self.generate_component_page(component_type, component_list)

        return pages

    def generate_all_tables(self, inventory: dict[str, Any]) -> dict[str, str]:
        """
        Generate just the table content for all component types (for marker-based updates).

        Args:
            inventory: Complete inventory data

        Returns:
            Dictionary mapping component_type to table content
        """
        tables = {}
        components = inventory.get("components", {})

        for component_type in ["receiver", "processor", "exporter", "connector", "extension"]:
            component_list = components.get(component_type, [])
            tables[component_type] = self.generate_table_only(component_type, component_list)

        return tables
