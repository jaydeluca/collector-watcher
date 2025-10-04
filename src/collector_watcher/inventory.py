"""Inventory management for component tracking."""

from pathlib import Path
from typing import Any

import yaml


class InventoryManager:
    """Manages component inventory storage and retrieval."""

    COMPONENT_TYPES = ["connector", "exporter", "extension", "processor", "receiver"]

    def __init__(self, inventory_dir: str = "data/inventory"):
        """
        Initialize the inventory manager.

        Args:
            inventory_dir: Directory to store inventory files
        """
        self.inventory_dir = Path(inventory_dir)

    def create_inventory(
        self,
        components: dict[str, list[dict[str, Any]]],
        repository: str = "opentelemetry-collector-contrib",
    ) -> dict[str, Any]:
        """
        Create inventory structure from scanned components.

        Args:
            components: Dictionary of component type to component list
            repository: Name of the repository being scanned

        Returns:
            Inventory dictionary with repository and components
        """
        inventory = {"repository": repository, "components": components}
        return inventory

    def save_inventory(self, inventory: dict[str, Any]) -> None:
        """
        Save inventory to separate YAML files per component type.

        Args:
            inventory: Inventory data to save
        """
        # Ensure directory exists
        self.inventory_dir.mkdir(parents=True, exist_ok=True)

        repository = inventory.get("repository", "")
        components = inventory.get("components", {})

        # Save each component type to its own file
        for component_type in self.COMPONENT_TYPES:
            component_list = components.get(component_type, [])
            file_path = self.inventory_dir / f"{component_type}.yaml"

            component_data = {
                "repository": repository,
                "component_type": component_type,
                "components": component_list,
            }

            with open(file_path, "w") as f:
                yaml.dump(
                    component_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True
                )

    def load_inventory(self) -> dict[str, Any]:
        """
        Load inventory from separate YAML files per component type.

        Returns:
            Inventory dictionary with all components, or empty structure if files don't exist
        """
        if not self.inventory_dir.exists():
            return {"repository": "", "components": {}}

        # Load each component type file
        components = {}
        repository = ""

        for component_type in self.COMPONENT_TYPES:
            file_path = self.inventory_dir / f"{component_type}.yaml"

            if file_path.exists():
                with open(file_path) as f:
                    data = yaml.safe_load(f) or {}
                    components[component_type] = data.get("components", [])
                    if not repository:
                        repository = data.get("repository", "")
            else:
                components[component_type] = []

        return {"repository": repository, "components": components}

    def inventory_exists(self) -> bool:
        """
        Check if inventory directory exists with at least one component file.

        Returns:
            True if inventory exists
        """
        if not self.inventory_dir.exists():
            return False

        # Check if at least one component file exists
        for component_type in self.COMPONENT_TYPES:
            if (self.inventory_dir / f"{component_type}.yaml").exists():
                return True

        return False
