"""Multi-repository scanner for OpenTelemetry Collector components."""

from pathlib import Path
from typing import Any

from collector_watcher.scanner import ComponentScanner


class MultiRepoScanner:
    """Scans multiple OpenTelemetry Collector repositories and merges results."""

    def __init__(self, repos: dict[str, str]):
        """
        Initialize the multi-repo scanner.

        Args:
            repos: Dict mapping repo name to local path
                   e.g., {"core": "/path/to/otel-collector",
                          "contrib": "/path/to/otel-collector-contrib"}
        """
        self.repos = repos
        self.scanners = {name: ComponentScanner(Path(path)) for name, path in repos.items()}

    def scan_all_repos(self) -> dict[str, Any]:
        """
        Scan all repositories and merge component data.

        Returns:
            Merged inventory with all components from all repos
        """
        # Scan each repository
        inventories = {}
        for name, scanner in self.scanners.items():
            components = scanner.scan_all_components()
            inventories[name] = components

        # Merge the results
        merged = self._merge_inventories(inventories)

        return merged

    def _merge_inventories(self, inventories: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """
        Merge component inventories from multiple repos.

        Args:
            inventories: Dict mapping repo name to its component inventory

        Returns:
            Merged inventory combining all components
        """
        # Start with empty merged inventory
        merged = {"repository": "opentelemetry-collector (merged)", "components": {}}

        # Component type order
        component_types = ["receiver", "processor", "exporter", "connector", "extension"]

        # For each component type
        for component_type in component_types:
            merged["components"][component_type] = []

            # Collect all components of this type from all repos
            components_by_name = {}

            for repo_name, inventory in inventories.items():
                components = inventory.get(component_type, [])
                for component in components:
                    name = component.get("name")
                    if not name:
                        continue

                    if name not in components_by_name:
                        # First time seeing this component
                        components_by_name[name] = {"repos": [repo_name], "component": component}
                    else:
                        # Component exists in multiple repos - merge them
                        components_by_name[name]["repos"].append(repo_name)
                        # Merge with preference to contrib metadata
                        if repo_name == "contrib":
                            components_by_name[name]["component"] = component

            # Build final component list with merged distribution info
            for _name, data in components_by_name.items():
                component = data["component"].copy()
                repos = data["repos"]

                # Update distributions in metadata
                if "metadata" not in component:
                    component["metadata"] = {}

                if "status" not in component["metadata"]:
                    component["metadata"]["status"] = {}

                # Set distributions based on which repos have this component
                distributions = []
                if "core" in repos:
                    distributions.append("core")
                if "contrib" in repos:
                    distributions.append("contrib")

                component["metadata"]["status"]["distributions"] = sorted(distributions)

                merged["components"][component_type].append(component)

            # Sort components alphabetically within each type
            merged["components"][component_type].sort(key=lambda c: c.get("name", ""))

        return merged
