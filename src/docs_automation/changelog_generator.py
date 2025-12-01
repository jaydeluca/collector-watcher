"""Generate changelog summaries for documentation updates."""

from typing import Any


class ChangelogGenerator:
    """Generates human-readable summaries of component changes between versions."""

    def __init__(self):
        """Initialize the changelog generator."""
        pass

    def _get_component_key(self, component: dict[str, Any]) -> str:
        """Get a unique key for a component."""
        return component.get("name", "unknown")

    def _get_stability_summary(self, component: dict[str, Any]) -> dict[str, str]:
        """Extract stability levels for all signals from a component."""
        metadata = component.get("metadata", {})
        status = metadata.get("status", {})
        stability = status.get("stability", {})

        signal_stability = {}
        for level, signals in stability.items():
            if isinstance(signals, list):
                for signal in signals:
                    signal_stability[signal] = level

        return signal_stability

    def _get_distributions(self, component: dict[str, Any]) -> set[str]:
        """Get the set of distributions for a component."""
        metadata = component.get("metadata", {})
        status = metadata.get("status", {})
        distributions = status.get("distributions", [])
        return set(distributions) if distributions else set()

    def compare_component_type(
        self,
        component_type: str,
        old_components: list[dict[str, Any]],
        new_components: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Compare components of a specific type between two versions.

        Args:
            component_type: Type of component (receiver, processor, etc.)
            old_components: Components from previous version
            new_components: Components from new version

        Returns:
            Dictionary containing:
            - added: List of newly added component names
            - removed: List of removed component names
            - stability_changed: List of components with stability changes
            - distribution_changed: List of components with distribution changes
        """
        # Create maps for easy lookup
        old_map = {self._get_component_key(c): c for c in old_components}
        new_map = {self._get_component_key(c): c for c in new_components}

        old_keys = set(old_map.keys())
        new_keys = set(new_map.keys())

        # Find additions and removals
        added = sorted(new_keys - old_keys)
        removed = sorted(old_keys - new_keys)

        # Find changes in existing components
        stability_changed = []
        distribution_changed = []

        for name in sorted(old_keys & new_keys):
            old_comp = old_map[name]
            new_comp = new_map[name]

            # Check stability changes (skip connectors as they have different stability model)
            if component_type != "connector":
                old_stability = self._get_stability_summary(old_comp)
                new_stability = self._get_stability_summary(new_comp)
                if old_stability != new_stability:
                    stability_changed.append(
                        {
                            "name": name,
                            "old": old_stability,
                            "new": new_stability,
                        }
                    )

            # Check distribution changes
            old_dists = self._get_distributions(old_comp)
            new_dists = self._get_distributions(new_comp)
            if old_dists != new_dists:
                distribution_changed.append(
                    {
                        "name": name,
                        "added": sorted(new_dists - old_dists),
                        "removed": sorted(old_dists - new_dists),
                    }
                )

        return {
            "added": added,
            "removed": removed,
            "stability_changed": stability_changed,
            "distribution_changed": distribution_changed,
        }

    def compare_inventories(
        self, old_inventory: dict[str, Any], new_inventory: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Compare two inventories and return a summary of changes.

        Args:
            old_inventory: Previous inventory
            new_inventory: New inventory

        Returns:
            Dictionary mapping component_type to changes
        """
        changes = {}

        old_components = old_inventory.get("components", {})
        new_components = new_inventory.get("components", {})

        all_types = set(old_components.keys()) | set(new_components.keys())

        for component_type in sorted(all_types):
            old_comps = old_components.get(component_type, [])
            new_comps = new_components.get(component_type, [])

            type_changes = self.compare_component_type(component_type, old_comps, new_comps)

            # Only include if there are actual changes
            if any(
                type_changes[key]
                for key in ["added", "removed", "stability_changed", "distribution_changed"]
            ):
                changes[component_type] = type_changes

        return changes

    def format_changes_markdown(self, changes: dict[str, Any]) -> str:
        """
        Format changes into a markdown summary.

        Args:
            changes: Changes dictionary from compare_inventories

        Returns:
            Markdown-formatted summary
        """
        if not changes:
            return "No significant changes detected."

        lines = ["## Summary of Changes\n"]

        for component_type in sorted(changes.keys()):
            type_changes = changes[component_type]
            type_title = component_type.capitalize()

            has_changes = False
            section_lines = [f"### {type_title}s\n"]

            # Added components
            if type_changes["added"]:
                has_changes = True
                section_lines.append("**New components:**")
                for name in type_changes["added"]:
                    section_lines.append(f"- `{name}`")
                section_lines.append("")

            # Removed components
            if type_changes["removed"]:
                has_changes = True
                section_lines.append("**Removed components:**")
                for name in type_changes["removed"]:
                    section_lines.append(f"- `{name}`")
                section_lines.append("")

            # Stability changes
            if type_changes["stability_changed"]:
                has_changes = True
                section_lines.append("**Stability changes:**")
                for change in type_changes["stability_changed"]:
                    name = change["name"]
                    old_stab = change["old"]
                    new_stab = change["new"]

                    # Find what changed
                    all_signals = set(old_stab.keys()) | set(new_stab.keys())
                    signal_changes = []
                    for signal in sorted(all_signals):
                        old_val = old_stab.get(signal, "-")
                        new_val = new_stab.get(signal, "-")
                        if old_val != new_val:
                            signal_changes.append(f"{signal}: {old_val} → {new_val}")

                    section_lines.append(f"- `{name}`: {', '.join(signal_changes)}")
                section_lines.append("")

            # Distribution changes
            if type_changes["distribution_changed"]:
                has_changes = True
                section_lines.append("**Distribution changes:**")
                for change in type_changes["distribution_changed"]:
                    name = change["name"]
                    added = change["added"]
                    removed = change["removed"]

                    change_desc = []
                    if added:
                        change_desc.append(f"added to {', '.join(added)}")
                    if removed:
                        change_desc.append(f"removed from {', '.join(removed)}")

                    section_lines.append(f"- `{name}`: {', '.join(change_desc)}")
                section_lines.append("")

            if has_changes:
                lines.extend(section_lines)

        return "\n".join(lines)

    def generate_summary(self, old_inventory: dict[str, Any], new_inventory: dict[str, Any]) -> str:
        """
        Generate a markdown summary of changes between two inventories.

        Args:
            old_inventory: Previous inventory
            new_inventory: New inventory

        Returns:
            Markdown-formatted summary
        """
        changes = self.compare_inventories(old_inventory, new_inventory)
        return self.format_changes_markdown(changes)
