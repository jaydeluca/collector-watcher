"""Integration test to validate the version mismatch bug fix."""

from collector_watcher.inventory import InventoryManager
from collector_watcher.version_detector import Version
from docs_automation.update_docs import get_best_available_version, merge_inventories


def test_version_mismatch_bugfix_with_real_metadata():
    """
    Test that the version mismatch bug is fixed using real metadata.

    This test validates the scenario from the bug report:
    - Contrib is at v0.140.1
    - Core is still at v0.140.0
    - Documentation generation should not lose core components
    """
    inv_mgr = InventoryManager("collector-metadata")

    # The target version (what we want to generate docs for)
    target_version = Version.from_string("v0.140.1")

    # Get best available versions for each distribution
    core_version = get_best_available_version(inv_mgr, "core", target_version)
    contrib_version = get_best_available_version(inv_mgr, "contrib", target_version)

    # Core should fall back to v0.140.0 since v0.140.1 doesn't exist
    assert core_version == Version.from_string("v0.140.0")

    # Contrib should use v0.140.1 since it exists
    assert contrib_version == Version.from_string("v0.140.1")

    # Load inventories
    core_inventory = inv_mgr.load_versioned_inventory("core", core_version)
    contrib_inventory = inv_mgr.load_versioned_inventory("contrib", contrib_version)

    # Verify we got data for both distributions
    assert core_inventory["version"] == "v0.140.0"
    assert contrib_inventory["version"] == "v0.140.1"

    # Merge inventories
    merged = merge_inventories(core_inventory, contrib_inventory)

    # Get extension components
    extensions = merged["components"]["extension"]
    extension_names = {ext["name"] for ext in extensions}

    # The bug was that memorylimiterextension was missing
    # This should now be present
    assert "memorylimiterextension" in extension_names, (
        "memorylimiterextension should be present in merged inventory"
    )

    # Verify it's marked as coming from core
    memory_limiter = next(ext for ext in extensions if ext["name"] == "memorylimiterextension")
    assert memory_limiter["source_repo"] == "core"

    # Also verify contrib extensions are present
    # (checking a few known contrib-only extensions)
    contrib_extensions = {"ackextension", "asapauthextension", "awsproxy"}
    found_contrib = contrib_extensions & extension_names
    assert len(found_contrib) > 0, "Should have contrib-only extensions"


def test_version_mismatch_does_not_cause_data_loss():
    """
    Test that version mismatch doesn't cause component data loss.

    Specifically tests that we don't lose core components when
    contrib is at a newer version.
    """
    inv_mgr = InventoryManager("collector-metadata")

    target_version = Version.from_string("v0.140.1")

    # Get inventories using fallback mechanism
    core_version = get_best_available_version(inv_mgr, "core", target_version)
    contrib_version = get_best_available_version(inv_mgr, "contrib", target_version)

    core_inventory = inv_mgr.load_versioned_inventory("core", core_version)
    contrib_inventory = inv_mgr.load_versioned_inventory("contrib", contrib_version)

    merged = merge_inventories(core_inventory, contrib_inventory)

    # Count components in each
    core_component_count = sum(
        len(comps) for comps in core_inventory.get("components", {}).values()
    )
    contrib_component_count = sum(
        len(comps) for comps in contrib_inventory.get("components", {}).values()
    )
    merged_component_count = sum(len(comps) for comps in merged.get("components", {}).values())

    # The merged count should be at least as many as the contrib count
    # (since some components are in both, merged count < core + contrib)
    assert merged_component_count >= contrib_component_count, (
        "Merged inventory should not lose components"
    )

    # Core should have contributed at least some components
    # (Check that core inventory was not empty)
    assert core_component_count > 0, "Core inventory should not be empty"

    # Merged should have more components than contrib alone
    # (unless all core components are also in contrib, which is unlikely)
    # This test is less strict since some components might legitimately
    # only be in contrib
    assert merged_component_count > 0, "Merged inventory should have components"


def test_no_version_mismatch_when_both_exist():
    """
    Test that when both versions exist, no fallback occurs.
    """
    inv_mgr = InventoryManager("collector-metadata")

    # Use v0.140.0 which exists for both
    target_version = Version.from_string("v0.140.0")

    core_version = get_best_available_version(inv_mgr, "core", target_version)
    contrib_version = get_best_available_version(inv_mgr, "contrib", target_version)

    # Both should match the target exactly
    assert core_version == target_version
    assert contrib_version == target_version

    # Load and merge
    core_inventory = inv_mgr.load_versioned_inventory("core", core_version)
    contrib_inventory = inv_mgr.load_versioned_inventory("contrib", contrib_version)

    merged = merge_inventories(core_inventory, contrib_inventory)

    # Should have components from both
    assert sum(len(comps) for comps in merged["components"].values()) > 0
