"""Main runner for collector watcher workflow."""

import json
import os
import sys
from pathlib import Path

from .detector import Change, ChangeDetector
from .inventory import InventoryManager
from .reporter import IssueReporter
from .scanner import ComponentScanner


class CollectorWatcher:
    """Orchestrates the collector watching workflow."""

    def __init__(self, repo_path: str, inventory_path: str = "data/inventory.yaml"):
        """
        Initialize the watcher.

        Args:
            repo_path: Path to the collector-contrib repository
            inventory_path: Path to store the inventory
        """
        self.repo_path = Path(repo_path)
        self.scanner = ComponentScanner(repo_path)
        self.inventory_manager = InventoryManager(inventory_path)

    def run_scan(self, detect_changes: bool = True) -> list[Change] | None:
        """
        Run a full scan and update inventory.

        Args:
            detect_changes: Whether to detect changes from previous inventory

        Returns:
            List of detected changes if detect_changes is True, None otherwise
        """
        print(f"Scanning repository: {self.repo_path}")

        # Load previous inventory if it exists
        old_inventory = None
        if detect_changes and self.inventory_manager.inventory_exists():
            old_inventory = self.inventory_manager.load_inventory()
            print("Loaded previous inventory for change detection")

        # Scan all components
        components = self.scanner.scan_all_components()

        # Print summary
        total_components = sum(len(comps) for comps in components.values())
        print(f"\nFound {total_components} total components:")
        for component_type, component_list in components.items():
            with_metadata = sum(1 for c in component_list if "metadata" in c)
            without_metadata = len(component_list) - with_metadata
            if without_metadata > 0:
                print(
                    f"  {component_type}: {len(component_list)} ({with_metadata} with metadata, {without_metadata} without)"
                )
            else:
                print(f"  {component_type}: {len(component_list)}")

        # Create new inventory
        new_inventory = self.inventory_manager.create_inventory(components)

        # Detect changes if requested
        changes = None
        if detect_changes and old_inventory:
            detector = ChangeDetector(old_inventory, new_inventory)
            changes = detector.detect_all_changes()

            if changes:
                print(f"\n🔍 Detected {len(changes)} change(s):")
                summary = detector.get_changes_summary()
                for change_type, count in sorted(summary.items()):
                    print(f"  - {change_type}: {count}")
            else:
                print("\n✓ No changes detected")

        # Save new inventory
        self.inventory_manager.save_inventory(new_inventory)
        print(f"\nInventory saved to: {self.inventory_manager.inventory_path}")

        return changes


def main():
    """CLI entry point for the watcher."""
    if len(sys.argv) < 2:
        print("Usage: python -m collector_watcher.runner <repo_path> [inventory_path] [OPTIONS]")
        print("\nOptions:")
        print("  --output-changes=FILE    Write changes to JSON file")
        print(
            "  --create-issues          Create GitHub issues for changes (requires GITHUB_TOKEN env var)"
        )
        print(
            "  --github-repo=REPO       GitHub repo for issues (default: jaydeluca/collector-watcher)"
        )
        print(
            "  --dry-run                Don't actually create issues, just show what would be created"
        )
        print("\nExample:")
        print("  python -m collector_watcher.runner /path/to/opentelemetry-collector-contrib")
        print("  python -m collector_watcher.runner /path/to/repo --output-changes=changes.json")
        print("  python -m collector_watcher.runner /path/to/repo --create-issues --dry-run")
        sys.exit(1)

    repo_path = sys.argv[1]
    inventory_path = "data/inventory.yaml"
    output_changes_file = None
    create_issues = False
    github_repo = "jaydeluca/collector-watcher"
    dry_run = False

    # Parse arguments
    for arg in sys.argv[2:]:
        if arg.startswith("--output-changes="):
            output_changes_file = arg.split("=", 1)[1]
        elif arg.startswith("--github-repo="):
            github_repo = arg.split("=", 1)[1]
        elif arg == "--create-issues":
            create_issues = True
        elif arg == "--dry-run":
            dry_run = True
        elif not arg.startswith("--"):
            inventory_path = arg

    try:
        watcher = CollectorWatcher(repo_path, inventory_path)
        changes = watcher.run_scan(detect_changes=True)

        # Write changes to file if requested
        if changes and output_changes_file:
            changes_data = [c.to_dict() for c in changes]
            with open(output_changes_file, "w") as f:
                json.dump(changes_data, f, indent=2)
            print(f"\n📄 Changes written to: {output_changes_file}")

        # Create GitHub issues if requested
        if changes and create_issues:
            github_token = os.environ.get("GITHUB_TOKEN")
            if not github_token:
                print("\n❌ GITHUB_TOKEN environment variable not set", file=sys.stderr)
                sys.exit(1)

            print(f"\n📝 Creating GitHub issues{' (DRY RUN)' if dry_run else ''}...")
            reporter = IssueReporter(github_token, github_repo)

            try:
                created_issues = reporter.create_issues_for_changes(changes, dry_run=dry_run)

                if created_issues:
                    print(f"✅ Created {len(created_issues)} issue(s):")
                    for issue in created_issues:
                        if dry_run:
                            print(f"  - [DRY RUN] {issue['title']}")
                        else:
                            print(f"  - #{issue['number']}: {issue['title']}")
                            print(f"    {issue['url']}")
                else:
                    print("  No new issues created (all were duplicates)")
            finally:
                reporter.close()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
