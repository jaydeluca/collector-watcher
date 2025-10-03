"""Component discovery for OpenTelemetry Collector repositories."""

from pathlib import Path
from typing import Any

from .parser import MetadataParser


class ComponentScanner:
    """Scans collector repositories for components."""

    # Component types to scan
    COMPONENT_TYPES = ["connector", "exporter", "extension", "processor", "receiver"]

    def __init__(self, repo_path: str):
        """
        Initialize the scanner.

        Args:
            repo_path: Path to the cloned collector-contrib repository
        """
        self.repo_path = Path(repo_path)
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")

    def scan_all_components(self) -> dict[str, list[dict[str, any]]]:
        """
        Scan all component types and return structured inventory.

        Returns:
            Dictionary mapping component types to lists of component info
        """
        components = {}
        for component_type in self.COMPONENT_TYPES:
            components[component_type] = self.scan_component_type(component_type)
        return components

    def scan_component_type(self, component_type: str) -> list[dict[str, any]]:
        """
        Scan a specific component type directory.

        Args:
            component_type: Type of component (receiver, processor, exporter)

        Returns:
            List of dictionaries containing component information
        """
        component_dir = self.repo_path / component_type
        if not component_dir.exists():
            return []

        components = []
        for item in sorted(component_dir.iterdir()):
            if item.is_dir() and self._is_component_directory(item):
                component_info = self._extract_component_info(item, component_type)
                components.append(component_info)

        return components

    def _is_component_directory(self, path: Path) -> bool:
        """
        Check if a directory is a valid component.

        A valid component directory typically contains:
        - go.mod file (indicating a Go module)
        - Or at least some .go files

        Args:
            path: Path to check

        Returns:
            True if this appears to be a component directory
        """
        # Exclude internal directories and test directories
        if path.name.startswith(".") or path.name.startswith("_"):
            return False
        if path.name in ["internal", "testdata"]:
            return False

        # Check for go.mod or .go files
        has_go_mod = (path / "go.mod").exists()
        has_go_files = any(path.glob("*.go"))

        return has_go_mod or has_go_files

    def _extract_component_info(self, component_path: Path, component_type: str) -> dict[str, Any]:
        """
        Extract information about a component.

        Args:
            component_path: Path to the component directory
            component_type: Type of component

        Returns:
            Dictionary with component information
        """
        parser = MetadataParser(component_path)
        has_metadata = parser.has_metadata()

        component_info = {
            "name": component_path.name,
        }

        # Parse and include metadata if present
        if has_metadata:
            parsed_metadata = parser.parse()
            if parsed_metadata:
                component_info["metadata"] = parsed_metadata
            else:
                # Metadata file exists but couldn't be parsed
                component_info["has_metadata"] = False
        else:
            # No metadata file
            component_info["has_metadata"] = False

        return component_info

    def get_components_with_metadata(self) -> set[str]:
        """
        Get a set of all component names that have metadata.yaml files.

        Returns:
            Set of component names with metadata
        """
        components = self.scan_all_components()
        with_metadata = set()

        for component_type, component_list in components.items():
            for component in component_list:
                if component["has_metadata"]:
                    with_metadata.add(f"{component_type}/{component['name']}")

        return with_metadata


def main():
    """Example usage of the scanner."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m collector_watcher.scanner <repo_path>")
        sys.exit(1)

    repo_path = sys.argv[1]
    scanner = ComponentScanner(repo_path)
    components = scanner.scan_all_components()

    print(f"Found components in {repo_path}:")
    for component_type, component_list in components.items():
        print(f"\n{component_type}: {len(component_list)} components")
        for component in component_list[:5]:  # Show first 5
            metadata_status = "✓" if component["has_metadata"] else "✗"
            print(f"  {metadata_status} {component['name']}")
        if len(component_list) > 5:
            print(f"  ... and {len(component_list) - 5} more")


if __name__ == "__main__":
    main()
