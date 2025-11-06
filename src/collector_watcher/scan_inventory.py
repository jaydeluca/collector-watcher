"""Main runner for collector watcher workflow."""

import sys
from pathlib import Path

from .inventory import InventoryManager
from .version_detector import Version
from .versioned_scanner import VersionedScanner


def main():
    """CLI entry point for the watcher."""
    if len(sys.argv) < 2:
        print(
            "Usage: python -m collector_watcher.scan_inventory <contrib_repo_path> --core-repo=<core_repo_path> [OPTIONS]"
        )
        print("\nRequired Options:")
        print("  --core-repo=PATH           Path to core collector repository")
        print("\nOptional Arguments:")
        print("  --inventory-dir=PATH       Inventory directory (default: collector-metadata)")
        print("  --mode=MODE                Scan mode: nightly, release, snapshot, specific")
        print("                             (default: nightly)")
        print("  --version=VERSION          Version for 'specific' mode (e.g., v0.112.0)")
        print("  --force                    Force rescan even if version exists")
        print("\nExamples:")
        print("  # Nightly scan (default) - check releases and update snapshots")
        print(
            "  python -m collector_watcher.scan_inventory /path/to/contrib --core-repo=/path/to/core"
        )
        print("\n  # Update snapshots only")
        print(
            "  python -m collector_watcher.scan_inventory /path/to/contrib --core-repo=/path/to/core --mode=snapshot"
        )
        print("\n  # Scan a specific version")
        print(
            "  python -m collector_watcher.scan_inventory /path/to/contrib --core-repo=/path/to/core --mode=specific --version=v0.112.0"
        )
        sys.exit(1)

    contrib_repo_path = sys.argv[1]
    inventory_dir = "collector-metadata"
    core_repo_path = None
    scan_mode = "nightly"
    specific_version = None
    force = False

    # Parse arguments
    for arg in sys.argv[2:]:
        if arg.startswith("--core-repo="):
            core_repo_path = arg.split("=", 1)[1]
        elif arg.startswith("--inventory-dir="):
            inventory_dir = arg.split("=", 1)[1]
        elif arg.startswith("--mode="):
            scan_mode = arg.split("=", 1)[1]
        elif arg.startswith("--version="):
            specific_version = arg.split("=", 1)[1]
        elif arg == "--force":
            force = True

    # Require core-repo
    if not core_repo_path:
        print("\n❌ Error: --core-repo is required", file=sys.stderr)
        print(
            "Usage: python -m collector_watcher.scan_inventory <contrib_repo_path> --core-repo=<core_repo_path>"
        )
        sys.exit(1)

    # Validate paths
    if not Path(contrib_repo_path).exists():
        print(
            f"\n❌ Error: Contrib repository path does not exist: {contrib_repo_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not Path(core_repo_path).exists():
        print(f"\n❌ Error: Core repository path does not exist: {core_repo_path}", file=sys.stderr)
        sys.exit(1)

    try:
        # Build distribution config
        dist_config = {
            "core": core_repo_path,
            "contrib": contrib_repo_path,
        }

        # Create inventory manager and versioned scanner
        inventory_manager = InventoryManager(inventory_dir)
        versioned_scanner = VersionedScanner(
            repos=dist_config,
            inventory_manager=inventory_manager,
        )

        # Run appropriate scan mode
        if scan_mode == "nightly":
            versioned_scanner.run_nightly_scan()

        elif scan_mode == "release":
            # Process latest releases only
            for dist in dist_config.keys():
                versioned_scanner.process_latest_release(dist)

        elif scan_mode == "snapshot":
            # Update snapshots only
            for dist in dist_config.keys():
                versioned_scanner.update_snapshot(dist)

        elif scan_mode == "specific":
            if not specific_version:
                print("Error: --version required for 'specific' mode")
                sys.exit(1)

            # Parse version
            try:
                version = Version.from_string(specific_version)
            except ValueError as e:
                print(f"Error: Invalid version format: {e}")
                sys.exit(1)

            # Scan both distributions at this version
            for dist in dist_config.keys():
                versioned_scanner.scan_specific_version(dist, version, force=force)

        else:
            print(f"Error: Unknown mode: {scan_mode}")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
