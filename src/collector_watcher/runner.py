"""Main runner for collector watcher workflow."""

import os
import sys
import tempfile
from pathlib import Path

from .doc_generator import DocGenerator
from .inventory import InventoryManager
from .multi_repo_scanner import MultiRepoScanner
from .pr_creator import PRCreator, generate_commit_message, generate_pr_body
from .scanner import ComponentScanner
from .version_detector import Version
from .versioned_scanner import VersionedScanner


class CollectorWatcher:
    """Orchestrates the collector watching workflow."""

    def __init__(
        self,
        repo_path: str,
        inventory_dir: str = "data/inventory",
        core_repo_path: str | None = None,
    ):
        """
        Initialize the watcher.

        Args:
            repo_path: Path to the collector-contrib repository
            inventory_dir: Directory to store inventory files
            core_repo_path: Optional path to the collector core repository
        """
        self.repo_path = Path(repo_path)
        self.core_repo_path = Path(core_repo_path) if core_repo_path else None

        # Use multi-repo scanner if core repo path is provided
        if self.core_repo_path:
            self.scanner = MultiRepoScanner(
                {
                    "core": str(self.core_repo_path),
                    "contrib": str(self.repo_path),
                }
            )
            self.is_multi_repo = True
        else:
            self.scanner = ComponentScanner(repo_path)
            self.is_multi_repo = False

        self.inventory_manager = InventoryManager(inventory_dir)

    def run_versioned_scan(
        self,
        mode: str = "nightly",
        specific_version: str | None = None,
        force: bool = False,
    ) -> dict:
        """
        Run versioned scan workflow.

        Args:
            mode: Scan mode - "nightly" (default), "release", "snapshot", or "specific"
            specific_version: Version string for "specific" mode (e.g., "v0.112.0")
            force: Force rescan even if version exists

        Returns:
            Summary of scan results
        """
        if not self.is_multi_repo:
            print("Error: Versioned scanning requires both core and contrib repos")
            print("Please provide --core-repo parameter")
            sys.exit(1)

        # Build distribution config
        dist_config = {
            "core": str(self.core_repo_path),
            "contrib": str(self.repo_path),
        }

        # Create versioned scanner
        versioned_scanner = VersionedScanner(
            repos=dist_config,
            inventory_manager=self.inventory_manager,
        )

        # Run appropriate scan mode
        if mode == "nightly":
            return versioned_scanner.run_nightly_scan()

        elif mode == "release":
            # Process latest releases only
            summary = {"new_releases": []}
            for dist in dist_config.keys():
                latest = versioned_scanner.process_latest_release(dist)
                if latest:
                    summary["new_releases"].append({"distribution": dist, "version": str(latest)})
            return summary

        elif mode == "snapshot":
            # Update snapshots only
            summary = {"snapshots_updated": []}
            for dist in dist_config.keys():
                snapshot = versioned_scanner.update_snapshot(dist)
                summary["snapshots_updated"].append(
                    {"distribution": dist, "version": str(snapshot)}
                )
            return summary

        elif mode == "specific":
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
            summary = {"scanned": []}
            for dist in dist_config.keys():
                versioned_scanner.scan_specific_version(dist, version, force=force)
                summary["scanned"].append({"distribution": dist, "version": str(version)})
            return summary

        else:
            print(f"Error: Unknown mode: {mode}")
            sys.exit(1)


def main():
    """CLI entry point for the watcher."""
    if len(sys.argv) < 2:
        print(
            "Usage: python -m collector_watcher.runner <contrib_repo_path> --core-repo=<core_repo_path> [OPTIONS]"
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
        print("  python -m collector_watcher.runner /path/to/contrib --core-repo=/path/to/core")
        print("\n  # Update snapshots only")
        print(
            "  python -m collector_watcher.runner /path/to/contrib --core-repo=/path/to/core --mode=snapshot"
        )
        print("\n  # Scan a specific version")
        print(
            "  python -m collector_watcher.runner /path/to/contrib --core-repo=/path/to/core --mode=specific --version=v0.112.0"
        )
        sys.exit(1)

    repo_path = sys.argv[1]
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
            "Usage: python -m collector_watcher.runner <contrib_repo_path> --core-repo=<core_repo_path>"
        )
        sys.exit(1)

    try:
        watcher = CollectorWatcher(repo_path, inventory_dir, core_repo_path=core_repo_path)
        watcher.run_versioned_scan(
            mode=scan_mode,
            specific_version=specific_version,
            force=force,
        )

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
