#!/usr/bin/env python3
"""
Update documentation pages locally for testing.

This script updates OpenTelemetry Collector component documentation tables
in your local opentelemetry.io repository using marker-based updates.

Usage:
    1. First scan repositories to update inventory:
       uv run python -m collector_watcher.scan_inventory /path/to/contrib --core-repo=/path/to/core

    2. Update documentation tables:
       uv run python -m docs_automation.update_docs [--version=v0.138.0] [--docs-repo=../opentelemetry.io]

    3. Preview the documentation:
       cd /path/to/opentelemetry.io
       hugo server
       # Open http://localhost:1313/docs/collector/components/
"""

import sys
from pathlib import Path

from collector_watcher.inventory import InventoryManager
from collector_watcher.version_detector import Version
from docs_automation.changelog_generator import ChangelogGenerator
from docs_automation.doc_generator import DocGenerator
from docs_automation.doc_updater import DocUpdater


def merge_inventories(core_inventory: dict, contrib_inventory: dict) -> dict:
    """
    Merge core and contrib inventories into a unified inventory.

    Components in both distributions will have their metadata merged,
    with distributions list showing both.

    Args:
        core_inventory: Core distribution inventory
        contrib_inventory: Contrib distribution inventory

    Returns:
        Merged inventory with unified components
    """
    merged = {"components": {}}

    # Get all component types
    all_types = set(core_inventory.get("components", {}).keys()) | set(
        contrib_inventory.get("components", {}).keys()
    )

    for component_type in all_types:
        core_comps = core_inventory.get("components", {}).get(component_type, [])
        contrib_comps = contrib_inventory.get("components", {}).get(component_type, [])

        # Create a map of component name to component data
        component_map = {}

        # Add core components (excluding experimental "x" components)
        for comp in core_comps:
            name = comp.get("name")
            # Skip experimental "x" components (e.g., xreceiver, xexporter, xconnector)
            if name == f"x{component_type}":
                continue
            comp_copy = comp.copy()
            comp_copy["source_repo"] = "core"
            component_map[name] = comp_copy

        # Merge or add contrib components (excluding experimental "x" components)
        for comp in contrib_comps:
            name = comp.get("name")
            # Skip experimental "x" components (e.g., xreceiver, xexporter, xconnector)
            if name == f"x{component_type}":
                continue
            if name in component_map:
                # Component exists in both - merge distributions
                # Source repo is CORE because that's where the code lives
                existing = component_map[name]
                existing_dists = (
                    existing.get("metadata", {}).get("status", {}).get("distributions", [])
                )
                contrib_dists = comp.get("metadata", {}).get("status", {}).get("distributions", [])

                # Combine and deduplicate distributions
                all_dists = sorted(set(existing_dists) | set(contrib_dists))

                # Update metadata with merged distributions
                if comp.get("metadata") and not existing.get("metadata"):
                    # Contrib has metadata but core doesn't - use contrib's
                    existing["metadata"] = comp["metadata"].copy()

                # Ensure metadata structure exists
                if "metadata" not in existing:
                    existing["metadata"] = {}
                if "status" not in existing["metadata"]:
                    existing["metadata"]["status"] = {}
                existing["metadata"]["status"]["distributions"] = all_dists

                # Keep source_repo as "core" since component is in core repo
            else:
                # Component only in contrib
                comp_copy = comp.copy()
                comp_copy["source_repo"] = "contrib"
                component_map[name] = comp_copy

        # Convert map back to list and sort alphabetically by name for consistent output
        merged["components"][component_type] = sorted(
            component_map.values(), key=lambda c: c.get("name", "")
        )

    return merged


def get_best_available_version(
    inv_mgr: InventoryManager, distribution: str, target_version: Version
) -> Version:
    """
    Get the best available version for a distribution.

    If the target version doesn't exist, fall back to the latest available version
    that is not newer than the target.

    Args:
        inv_mgr: Inventory manager
        distribution: Distribution name
        target_version: Desired version

    Returns:
        Best available version (may be older than target if target doesn't exist)
    """
    if inv_mgr.version_exists(distribution, target_version):
        return target_version

    # Get all non-snapshot versions
    all_versions = [v for v in inv_mgr.list_versions(distribution) if not v.is_snapshot]

    if not all_versions:
        raise ValueError(f"No versions found for {distribution}")

    # Find the latest version that's not newer than target
    # (versions are sorted newest to oldest)
    for version in all_versions:
        if version <= target_version:
            return version

    # If no suitable version found, use the oldest available
    return all_versions[-1]


def main():
    """Update docs in local opentelemetry.io repository."""
    # Parse arguments
    version_str = None
    docs_repo_path = "../opentelemetry.io"

    for arg in sys.argv[1:]:
        if arg.startswith("--version="):
            version_str = arg.split("=", 1)[1]
        elif arg.startswith("--docs-repo="):
            docs_repo_path = arg.split("=", 1)[1]

    # Load inventory manager
    print("Loading inventory...")
    inv_mgr = InventoryManager("collector-metadata")

    # Determine which version to use (check contrib first)
    if version_str:
        version = Version.from_string(version_str)
    else:
        # Use the latest non-snapshot version from contrib
        versions = inv_mgr.list_versions("contrib")
        if not versions:
            print("❌ No versions found for contrib")
            sys.exit(1)

        # Filter out snapshots and get the latest
        release_versions = [v for v in versions if not v.is_snapshot]
        if not release_versions:
            print("❌ No release versions found for contrib")
            sys.exit(1)

        version = release_versions[0]

    print(f"Target version: {version}")

    # Get best available versions for each distribution
    core_version = get_best_available_version(inv_mgr, "core", version)
    contrib_version = get_best_available_version(inv_mgr, "contrib", version)

    if core_version != version or contrib_version != version:
        print("\n⚠️  Version mismatch detected:")
        print(f"   Core:    {core_version}" + (" (fallback)" if core_version != version else ""))
        print(
            f"   Contrib: {contrib_version}" + (" (fallback)" if contrib_version != version else "")
        )
        print()

    # Load both core and contrib inventories
    print(f"Loading core inventory ({core_version})...")
    core_inventory = inv_mgr.load_versioned_inventory("core", core_version)

    print(f"Loading contrib inventory ({contrib_version})...")
    contrib_inventory = inv_mgr.load_versioned_inventory("contrib", contrib_version)

    # Merge inventories
    print("Merging inventories...")
    merged_inventory = merge_inventories(core_inventory, contrib_inventory)

    total_components = sum(len(comps) for comps in merged_inventory["components"].values())
    print(f"Loaded {total_components} total components")

    # Generate changelog if we have a previous version
    changelog_summary = None
    try:
        # Find the previous version for comparison
        all_versions = [v for v in inv_mgr.list_versions("contrib") if not v.is_snapshot]
        if len(all_versions) > 1:
            # Get the version before the current one
            current_idx = all_versions.index(contrib_version)
            if current_idx < len(all_versions) - 1:
                prev_version = all_versions[current_idx + 1]
                print(f"\nGenerating changelog (comparing {prev_version} → {contrib_version})...")

                # Load previous inventories
                prev_core_version = get_best_available_version(inv_mgr, "core", prev_version)
                prev_contrib_version = get_best_available_version(inv_mgr, "contrib", prev_version)

                prev_core_inv = inv_mgr.load_versioned_inventory("core", prev_core_version)
                prev_contrib_inv = inv_mgr.load_versioned_inventory("contrib", prev_contrib_version)
                prev_merged = merge_inventories(prev_core_inv, prev_contrib_inv)

                # Generate changelog
                changelog_gen = ChangelogGenerator()
                changelog_summary = changelog_gen.generate_summary(prev_merged, merged_inventory)
                print(changelog_summary)

                # Save changelog to file for GitHub workflow to use in PR body
                changelog_file = Path("changelog_summary.md")
                changelog_file.write_text(changelog_summary)
                print(f"\n✅ Changelog saved to {changelog_file}")
    except Exception as e:
        print(f"⚠️  Could not generate changelog: {e}")

    # Generate table content
    print("\nGenerating component tables...")
    doc_gen = DocGenerator(version=str(version))
    tables = doc_gen.generate_all_component_tables(merged_inventory)

    print(f"Generated {len(tables)} component tables")

    # Setup doc updater
    updater = DocUpdater()

    # Check docs repo exists
    docs_repo = Path(docs_repo_path)
    if not docs_repo.exists():
        print(f"\n❌ Error: {docs_repo} does not exist")
        return

    # Update each component type page
    components_dir = docs_repo / "content/en/docs/collector/components"

    if not components_dir.exists():
        print(f"\n❌ Error: {components_dir} does not exist")
        print(
            "Please ensure the opentelemetry.io repository has the collector components directory"
        )
        return

    print(f"\nUpdating pages in {components_dir}...")
    updated_count = 0

    for component_type, table_content in tables.items():
        page_path = components_dir / f"{component_type}.md"

        if not page_path.exists():
            print(f"  ⚠️  {component_type}.md not found, skipping")
            continue

        # Update the table section
        marker_id = f"{component_type}-table"
        success = updater.update_file(page_path, marker_id, table_content)

        if success:
            print(f"  ✓ {component_type}.md")
            updated_count += 1
        else:
            print(f"  ⚠️  {component_type}.md - markers not found")

    if updated_count > 0:
        print(f"\n✅ Done! Updated {updated_count} page(s)")
        print("\nTo view the pages:")
        print(f"  cd {docs_repo}")
        print("  hugo server")
        print("  Open http://localhost:1313/docs/collector/components/")
    else:
        print("\n⚠️  No pages were updated. Make sure the pages have the correct markers:")
        print("  <!-- BEGIN GENERATED: {component-type}-table SOURCE: collector-watcher -->")
        print("  <!-- END GENERATED: {component-type}-table SOURCE: collector-watcher -->")


if __name__ == "__main__":
    main()
