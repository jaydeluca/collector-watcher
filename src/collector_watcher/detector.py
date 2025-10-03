"""Change detection for component inventory."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ChangeType(Enum):
    """Types of changes that can be detected."""

    COMPONENT_ADDED = "component_added"
    COMPONENT_REMOVED = "component_removed"
    METADATA_ADDED = "metadata_added"
    METADATA_REMOVED = "metadata_removed"
    STABILITY_CHANGED = "stability_changed"
    ATTRIBUTE_ADDED = "attribute_added"
    ATTRIBUTE_REMOVED = "attribute_removed"
    ATTRIBUTE_MODIFIED = "attribute_modified"
    METRIC_ADDED = "metric_added"
    METRIC_REMOVED = "metric_removed"
    METRIC_MODIFIED = "metric_modified"


@dataclass
class Change:
    """Represents a single detected change."""

    change_type: ChangeType
    component_type: str  # receiver, processor, exporter
    component_name: str
    description: str
    old_value: Any = None
    new_value: Any = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "change_type": self.change_type.value,
            "component_type": self.component_type,
            "component_name": self.component_name,
            "description": self.description,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "details": self.details,
        }


class ChangeDetector:
    """Detects changes between two inventory snapshots."""

    def __init__(self, old_inventory: dict[str, Any], new_inventory: dict[str, Any]):
        """
        Initialize the detector.

        Args:
            old_inventory: Previous inventory dictionary
            new_inventory: Current inventory dictionary
        """
        self.old_inventory = old_inventory
        self.new_inventory = new_inventory
        self.changes: list[Change] = []

    def detect_all_changes(self) -> list[Change]:
        """
        Detect all changes between inventories.

        Returns:
            List of Change objects
        """
        self.changes = []

        old_components = self.old_inventory.get("components", {})
        new_components = self.new_inventory.get("components", {})

        # Process each component type
        for component_type in ["connector", "exporter", "extension", "processor", "receiver"]:
            old_comps = {c["name"]: c for c in old_components.get(component_type, [])}
            new_comps = {c["name"]: c for c in new_components.get(component_type, [])}

            self._detect_component_changes(component_type, old_comps, new_comps)

        return self.changes

    def _detect_component_changes(
        self,
        component_type: str,
        old_components: dict[str, dict],
        new_components: dict[str, dict],
    ) -> None:
        """
        Detect changes for a specific component type.

        Args:
            component_type: Type of component (receiver, processor, exporter)
            old_components: Dictionary of old components by name
            new_components: Dictionary of new components by name
        """
        old_names = set(old_components.keys())
        new_names = set(new_components.keys())

        # Detect additions
        for name in sorted(new_names - old_names):
            self.changes.append(
                Change(
                    change_type=ChangeType.COMPONENT_ADDED,
                    component_type=component_type,
                    component_name=name,
                    description=f"New {component_type} component added: {name}",
                    new_value=new_components[name],
                )
            )

        # Detect removals
        for name in sorted(old_names - new_names):
            self.changes.append(
                Change(
                    change_type=ChangeType.COMPONENT_REMOVED,
                    component_type=component_type,
                    component_name=name,
                    description=f"Component removed: {component_type}/{name}",
                    old_value=old_components[name],
                )
            )

        # Detect modifications in existing components
        for name in sorted(old_names & new_names):
            self._detect_metadata_changes(
                component_type, name, old_components[name], new_components[name]
            )

    def _detect_metadata_changes(
        self,
        component_type: str,
        component_name: str,
        old_component: dict,
        new_component: dict,
    ) -> None:
        """
        Detect metadata changes for a specific component.

        Args:
            component_type: Type of component
            component_name: Name of component
            old_component: Old component data
            new_component: New component data
        """
        # Check if metadata exists - either explicit field or presence of metadata key
        old_has_metadata = "metadata" in old_component or old_component.get("has_metadata", False)
        new_has_metadata = "metadata" in new_component or new_component.get("has_metadata", False)

        # Metadata added
        if not old_has_metadata and new_has_metadata:
            self.changes.append(
                Change(
                    change_type=ChangeType.METADATA_ADDED,
                    component_type=component_type,
                    component_name=component_name,
                    description=f"Metadata added to {component_type}/{component_name}",
                    new_value=new_component.get("metadata"),
                )
            )
            return

        # Metadata removed
        if old_has_metadata and not new_has_metadata:
            self.changes.append(
                Change(
                    change_type=ChangeType.METADATA_REMOVED,
                    component_type=component_type,
                    component_name=component_name,
                    description=f"Metadata removed from {component_type}/{component_name}",
                    old_value=old_component.get("metadata"),
                )
            )
            return

        # Both have metadata - check for changes
        if old_has_metadata and new_has_metadata:
            old_metadata = old_component.get("metadata", {})
            new_metadata = new_component.get("metadata", {})

            self._detect_stability_changes(
                component_type, component_name, old_metadata, new_metadata
            )
            self._detect_attribute_changes(
                component_type, component_name, old_metadata, new_metadata
            )
            self._detect_metric_changes(component_type, component_name, old_metadata, new_metadata)

    def _detect_stability_changes(
        self,
        component_type: str,
        component_name: str,
        old_metadata: dict,
        new_metadata: dict,
    ) -> None:
        """Detect changes in stability levels."""
        old_stability = old_metadata.get("status", {}).get("stability", {})
        new_stability = new_metadata.get("status", {}).get("stability", {})

        if old_stability != new_stability:
            self.changes.append(
                Change(
                    change_type=ChangeType.STABILITY_CHANGED,
                    component_type=component_type,
                    component_name=component_name,
                    description=f"Stability changed for {component_type}/{component_name}",
                    old_value=old_stability,
                    new_value=new_stability,
                    details={
                        "old_stability": old_stability,
                        "new_stability": new_stability,
                    },
                )
            )

    def _detect_attribute_changes(
        self,
        component_type: str,
        component_name: str,
        old_metadata: dict,
        new_metadata: dict,
    ) -> None:
        """Detect changes in attributes."""
        old_attrs = old_metadata.get("attributes", {})
        new_attrs = new_metadata.get("attributes", {})

        old_attr_names = set(old_attrs.keys())
        new_attr_names = set(new_attrs.keys())

        # Attribute additions
        for attr_name in sorted(new_attr_names - old_attr_names):
            self.changes.append(
                Change(
                    change_type=ChangeType.ATTRIBUTE_ADDED,
                    component_type=component_type,
                    component_name=component_name,
                    description=f"Attribute '{attr_name}' added to {component_type}/{component_name}",
                    new_value=new_attrs[attr_name],
                    details={"attribute_name": attr_name},
                )
            )

        # Attribute removals
        for attr_name in sorted(old_attr_names - new_attr_names):
            self.changes.append(
                Change(
                    change_type=ChangeType.ATTRIBUTE_REMOVED,
                    component_type=component_type,
                    component_name=component_name,
                    description=f"Attribute '{attr_name}' removed from {component_type}/{component_name}",
                    old_value=old_attrs[attr_name],
                    details={"attribute_name": attr_name},
                )
            )

        # Attribute modifications
        for attr_name in sorted(old_attr_names & new_attr_names):
            if old_attrs[attr_name] != new_attrs[attr_name]:
                self.changes.append(
                    Change(
                        change_type=ChangeType.ATTRIBUTE_MODIFIED,
                        component_type=component_type,
                        component_name=component_name,
                        description=f"Attribute '{attr_name}' modified in {component_type}/{component_name}",
                        old_value=old_attrs[attr_name],
                        new_value=new_attrs[attr_name],
                        details={"attribute_name": attr_name},
                    )
                )

    def _detect_metric_changes(
        self,
        component_type: str,
        component_name: str,
        old_metadata: dict,
        new_metadata: dict,
    ) -> None:
        """Detect changes in metrics."""
        old_metrics = old_metadata.get("metrics", {})
        new_metrics = new_metadata.get("metrics", {})

        old_metric_names = set(old_metrics.keys())
        new_metric_names = set(new_metrics.keys())

        # Metric additions
        for metric_name in sorted(new_metric_names - old_metric_names):
            self.changes.append(
                Change(
                    change_type=ChangeType.METRIC_ADDED,
                    component_type=component_type,
                    component_name=component_name,
                    description=f"Metric '{metric_name}' added to {component_type}/{component_name}",
                    new_value=new_metrics[metric_name],
                    details={"metric_name": metric_name},
                )
            )

        # Metric removals
        for metric_name in sorted(old_metric_names - new_metric_names):
            self.changes.append(
                Change(
                    change_type=ChangeType.METRIC_REMOVED,
                    component_type=component_type,
                    component_name=component_name,
                    description=f"Metric '{metric_name}' removed from {component_type}/{component_name}",
                    old_value=old_metrics[metric_name],
                    details={"metric_name": metric_name},
                )
            )

        # Metric modifications
        for metric_name in sorted(old_metric_names & new_metric_names):
            if old_metrics[metric_name] != new_metrics[metric_name]:
                self.changes.append(
                    Change(
                        change_type=ChangeType.METRIC_MODIFIED,
                        component_type=component_type,
                        component_name=component_name,
                        description=f"Metric '{metric_name}' modified in {component_type}/{component_name}",
                        old_value=old_metrics[metric_name],
                        new_value=new_metrics[metric_name],
                        details={"metric_name": metric_name},
                    )
                )

    def has_changes(self) -> bool:
        """Check if any changes were detected."""
        return len(self.changes) > 0

    def get_changes_by_type(self, change_type: ChangeType) -> list[Change]:
        """Get all changes of a specific type."""
        return [c for c in self.changes if c.change_type == change_type]

    def get_changes_summary(self) -> dict[str, int]:
        """Get a summary of changes by type."""
        summary = {}
        for change in self.changes:
            key = change.change_type.value
            summary[key] = summary.get(key, 0) + 1
        return summary
