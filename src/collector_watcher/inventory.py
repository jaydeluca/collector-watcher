"""Inventory management for component tracking."""

from pathlib import Path
from typing import Any

import yaml


class InventoryManager:
    """Manages component inventory storage and retrieval."""

    def __init__(self, inventory_path: str = "data/inventory.yaml"):
        """
        Initialize the inventory manager.

        Args:
            inventory_path: Path to the inventory file
        """
        self.inventory_path = Path(inventory_path)

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
            Inventory dictionary ready for serialization
        """
        inventory = {"repository": repository, "components": components}
        return inventory

    def save_inventory(self, inventory: dict[str, Any]) -> None:
        """
        Save inventory to YAML file.

        Args:
            inventory: Inventory data to save
        """
        # Ensure directory exists
        self.inventory_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.inventory_path, "w") as f:
            yaml.dump(inventory, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    def load_inventory(self) -> dict[str, Any]:
        """
        Load inventory from YAML file.

        Returns:
            Inventory dictionary, or empty structure if file doesn't exist
        """
        if not self.inventory_path.exists():
            return {"repository": "", "components": {}}

        with open(self.inventory_path) as f:
            return yaml.safe_load(f) or {"repository": "", "components": {}}

    def inventory_exists(self) -> bool:
        """
        Check if inventory file exists.

        Returns:
            True if inventory file exists
        """
        return self.inventory_path.exists()
