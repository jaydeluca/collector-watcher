"""Documentation generator for OpenTelemetry Collector components."""

from typing import Any


class DocGenerator:
    """Generates component tables for marker-based documentation updates."""

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

    def _is_unmaintained(self, component: dict[str, Any]) -> bool:
        """
        Check if a component is unmaintained.

        A component is considered unmaintained if any of its signals
        have an "unmaintained" stability level.

        Args:
            component: Component data

        Returns:
            True if component is unmaintained
        """
        metadata = component.get("metadata", {})
        if not metadata:
            return False

        status = metadata.get("status", {})
        stability = status.get("stability", {})

        # Check if "unmaintained" is one of the stability levels
        return "unmaintained" in stability

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

        if component_type == "extension":
            table_content += "| Name | Distributions[^1] | Stability[^2] |\n"
            table_content += "|------|-------------------|---------------|\n"
        else:
            table_content += "| Name | Distributions[^1] | Traces[^2] | Metrics[^2] | Logs[^2] |\n"
            table_content += "|------|-------------------|------------|-------------|----------|\n"

        for component in components:
            name = component.get("name", "unknown")
            metadata = component.get("metadata", {})

            distributions = self._get_distributions(component)
            distributions_str = self._format_distributions(distributions)
            stability_map = self.get_stability_by_signal(metadata)
            source_repo = component.get("source_repo", "contrib")

            if source_repo == "core":
                repo_name = "opentelemetry-collector"
            else:
                repo_name = "opentelemetry-collector-contrib"

            repo_url = f"https://github.com/open-telemetry/{repo_name}"
            component_path = f"{component_type}/{name}"
            readme_link = f"{repo_url}/tree/main/{component_path}"
            name_link = f"[{name}]({readme_link})"

            # Add unmaintained emoji if component has no active maintainers
            if self._is_unmaintained(component):
                name_link += " ⚠️"

            if component_type == "extension":
                stability = stability_map.get("extension", "N/A")
                table_content += f"| {name_link} | {distributions_str} | {stability} |\n"
            else:
                traces = stability_map.get("traces", "-")
                metrics = stability_map.get("metrics", "-")
                logs = stability_map.get("logs", "-")
                table_content += (
                    f"| {name_link} | {distributions_str} | {traces} | {metrics} | {logs} |\n"
                )

        table_content += "\n"
        stability_link = "https://github.com/open-telemetry/opentelemetry-collector/blob/main/docs/component-stability.md"

        table_content += (
            "⚠️ **Note:** Components marked with ⚠️ are unmaintained and have no active codeowners. They may not receive regular updates or bug fixes.\n\n"
            "[^1]: Shows which distributions (core, contrib, k8s, etc.) include this component.\n"
            f"[^2]: For details about component stability levels, see the [OpenTelemetry Collector component stability definitions]({stability_link}).\n"
        )

        return table_content

    def generate_component_table(
        self, component_type: str, components: list[dict[str, Any]]
    ) -> str:
        """
        Generate table content for a component type (for marker-based updates).

        Args:
            component_type: Type of component (receiver, processor, etc.)
            components: List of components of this type

        Returns:
            Markdown table content (no front matter or headers)
        """
        sorted_components = sorted(components, key=lambda c: c.get("name", ""))
        return self._generate_component_table(component_type, sorted_components)

    def generate_all_component_tables(self, inventory: dict[str, Any]) -> dict[str, str]:
        """
        Generate table content for all component types (for marker-based updates).

        Args:
            inventory: Complete inventory data

        Returns:
            Dictionary mapping component_type to table content
        """
        tables = {}
        components = inventory.get("components", {})

        for component_type in ["receiver", "processor", "exporter", "connector", "extension"]:
            component_list = components.get(component_type, [])
            tables[component_type] = self.generate_component_table(component_type, component_list)

        return tables
