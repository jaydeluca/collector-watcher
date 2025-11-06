"""Component discovery for OpenTelemetry Collector repositories."""

from pathlib import Path
from typing import Any

from .parser import MetadataParser


class ComponentScanner:
    """Scans collector repositories for components."""

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

        A valid component directory typically contains go.mod or .go files,
        and excludes internal/test/utility directories.

        Args:
            path: Path to check

        Returns:
            True if this appears to be a component directory
        """
        if path.name.startswith(".") or path.name.startswith("_"):
            return False
        if path.name in ["internal", "testdata"]:
            return False

        if path.name.endswith("test") or path.name.endswith("helper"):
            return False

        excluded_prefixes = [
            "encoding",
            "observer",
            "storage",
            "extensionauth",
            "extensioncapabilities",
            "extensionmiddleware",
            "opampcustommessages",
        ]
        if path.name in excluded_prefixes:
            return False

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

        if has_metadata:
            parsed_metadata = parser.parse()
            if parsed_metadata:
                component_info["metadata"] = parsed_metadata
            else:
                component_info["has_metadata"] = False
        else:
            component_info["has_metadata"] = False

        return component_info
