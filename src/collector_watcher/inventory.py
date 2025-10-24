"""Inventory management for component tracking."""

import shutil
from pathlib import Path
from typing import Any, Literal

import yaml

from .version_detector import Version

DistributionName = Literal["core", "contrib"]


class InventoryManager:
    """Manages component inventory storage and retrieval."""

    COMPONENT_TYPES = ["connector", "exporter", "extension", "processor", "receiver"]

    def __init__(self, inventory_dir: str = "collector-metadata"):
        """
        Initialize the inventory manager.

        Args:
            inventory_dir: Base directory for versioned metadata (default: collector-metadata)
        """
        self.inventory_dir = Path(inventory_dir)

    def get_version_dir(self, distribution: DistributionName, version: Version) -> Path:
        """
        Get the directory path for a specific distribution and version.

        Args:
            distribution: Distribution name (core or contrib)
            version: Version object

        Returns:
            Path to version directory
        """
        return self.inventory_dir / distribution / str(version)

    def save_versioned_inventory(
        self,
        distribution: DistributionName,
        version: Version,
        components: dict[str, list[dict[str, Any]]],
        repository: str,
    ) -> None:
        """
        Save inventory for a specific distribution and version.

        Args:
            distribution: Distribution name (core or contrib)
            version: Version object
            components: Dictionary of component type to component list
            repository: Name of the repository being scanned
        """
        version_dir = self.get_version_dir(distribution, version)
        version_dir.mkdir(parents=True, exist_ok=True)

        # Save each component type to its own file
        for component_type in self.COMPONENT_TYPES:
            component_list = components.get(component_type, [])
            file_path = version_dir / f"{component_type}.yaml"

            component_data = {
                "distribution": distribution,
                "version": str(version),
                "repository": repository,
                "component_type": component_type,
                "components": component_list,
            }

            with open(file_path, "w") as f:
                yaml.dump(
                    component_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True
                )

    def load_versioned_inventory(
        self, distribution: DistributionName, version: Version
    ) -> dict[str, Any]:
        """
        Load inventory for a specific distribution and version.

        Args:
            distribution: Distribution name
            version: Version object

        Returns:
            Inventory dictionary with all components, or empty structure if doesn't exist
        """
        version_dir = self.get_version_dir(distribution, version)

        if not version_dir.exists():
            return {"distribution": distribution, "version": str(version), "components": {}}

        # Load each component type file
        components = {}
        repository = ""

        for component_type in self.COMPONENT_TYPES:
            file_path = version_dir / f"{component_type}.yaml"

            if file_path.exists():
                with open(file_path) as f:
                    data = yaml.safe_load(f) or {}
                    components[component_type] = data.get("components", [])
                    if not repository:
                        repository = data.get("repository", "")
            else:
                components[component_type] = []

        return {
            "distribution": distribution,
            "version": str(version),
            "repository": repository,
            "components": components,
        }

    def list_versions(self, distribution: DistributionName) -> list[Version]:
        """
        List all available versions for a distribution.

        Args:
            distribution: Distribution name

        Returns:
            List of versions, sorted newest to oldest
        """
        dist_dir = self.inventory_dir / distribution
        if not dist_dir.exists():
            return []

        versions = []
        for item in dist_dir.iterdir():
            if item.is_dir():
                try:
                    version = Version.from_string(item.name)
                    versions.append(version)
                except ValueError:
                    # Skip directories that aren't valid versions
                    continue

        return sorted(versions, reverse=True)

    def list_snapshot_versions(self, distribution: DistributionName) -> list[Version]:
        """
        List all snapshot versions for a distribution.

        Args:
            distribution: Distribution name

        Returns:
            List of snapshot versions
        """
        all_versions = self.list_versions(distribution)
        return [v for v in all_versions if v.is_snapshot]

    def cleanup_snapshots(self, distribution: DistributionName) -> int:
        """
        Remove all snapshot versions for a distribution.

        Args:
            distribution: Distribution name

        Returns:
            Number of snapshot versions removed
        """
        snapshots = self.list_snapshot_versions(distribution)
        count = 0

        for snapshot in snapshots:
            snapshot_dir = self.get_version_dir(distribution, snapshot)
            if snapshot_dir.exists():
                shutil.rmtree(snapshot_dir)
                count += 1

        return count

    def version_exists(self, distribution: DistributionName, version: Version) -> bool:
        """
        Check if a specific version exists for a distribution.

        Args:
            distribution: Distribution name
            version: Version to check

        Returns:
            True if version directory exists
        """
        version_dir = self.get_version_dir(distribution, version)
        return version_dir.exists()
