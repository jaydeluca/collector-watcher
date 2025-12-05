"""Component discovery for OpenTelemetry Collector repositories."""

from pathlib import Path
from typing import Any

from .parser import MetadataParser


class ComponentScanner:
    """Scans collector repositories for components."""

    COMPONENT_TYPES = ["connector", "exporter", "extension", "processor", "receiver"]

    # Directories that contain nested components (subtypes)
    # Maps parent directory name to subtype name
    NESTED_COMPONENT_DIRS = {
        "encoding": "encoding",
        "observer": "observer",
        "storage": "storage",
    }

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
            if item.is_dir():
                # Check if this is a nested component directory (e.g., extension/encoding)
                if item.name in self.NESTED_COMPONENT_DIRS:
                    nested_components = self._scan_nested_components(
                        item, component_type, self.NESTED_COMPONENT_DIRS[item.name]
                    )
                    components.extend(nested_components)
                elif self._is_component_directory(item):
                    component_info = self._extract_component_info(item, component_type)
                    components.append(component_info)

        return components

    def _scan_nested_components(
        self, nested_dir: Path, component_type: str, subtype: str
    ) -> list[dict[str, Any]]:
        """
        Scan a nested component directory (e.g., extension/encoding).

        Args:
            nested_dir: Path to the nested directory
            component_type: Type of component (e.g., extension)
            subtype: Subtype name (e.g., encoding, observer, storage)

        Returns:
            List of component dictionaries with subtype field set
        """
        components = []
        for item in sorted(nested_dir.iterdir()):
            if item.is_dir() and self._is_nested_component_directory(item):
                component_info = self._extract_component_info(item, component_type, subtype=subtype)
                components.append(component_info)
        return components

    def _is_nested_component_directory(self, path: Path) -> bool:
        """
        Check if a directory is a valid nested component.

        Similar to _is_component_directory but for nested components.

        Args:
            path: Path to check

        Returns:
            True if this appears to be a nested component directory
        """
        if path.name.startswith(".") or path.name.startswith("_"):
            return False
        if path.name in ["internal", "testdata"]:
            return False
        if path.name.endswith("test") or path.name.endswith("helper"):
            return False

        # Must have go.mod or .go files
        has_go_mod = (path / "go.mod").exists()
        has_go_files = any(path.glob("*.go"))

        return has_go_mod or has_go_files

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

        # These directories are handled separately as nested component directories
        # or are utility packages that aren't actual components
        excluded_dirs = [
            "extensionauth",
            "extensioncapabilities",
            "extensionmiddleware",
            "opampcustommessages",
        ]
        if path.name in excluded_dirs:
            return False

        # Nested component directories are handled separately
        if path.name in self.NESTED_COMPONENT_DIRS:
            return False

        has_go_mod = (path / "go.mod").exists()
        has_go_files = any(path.glob("*.go"))

        return has_go_mod or has_go_files

    def _extract_component_info(
        self, component_path: Path, component_type: str, subtype: str | None = None
    ) -> dict[str, Any]:
        """
        Extract information about a component.

        Args:
            component_path: Path to the component directory
            component_type: Type of component
            subtype: Optional subtype (e.g., "encoding", "observer", "storage")

        Returns:
            Dictionary with component information
        """
        parser = MetadataParser(component_path)
        has_metadata = parser.has_metadata()

        component_info = {
            "name": component_path.name,
        }

        # Add subtype if this is a nested component
        if subtype:
            component_info["subtype"] = subtype

        if has_metadata:
            parsed_metadata = parser.parse()
            if parsed_metadata:
                component_info["metadata"] = parsed_metadata
            else:
                component_info["has_metadata"] = False
        else:
            component_info["has_metadata"] = False

        return component_info
