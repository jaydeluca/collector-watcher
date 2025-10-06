"""Main runner for collector watcher workflow."""

import json
import os
import sys
import tempfile
from pathlib import Path

from .detector import Change, ChangeDetector
from .doc_generator import DocGenerator
from .inventory import InventoryManager
from .multi_repo_scanner import MultiRepoScanner
from .pr_creator import PRCreator, generate_commit_message, generate_pr_body
from .reporter import IssueReporter
from .scanner import ComponentScanner


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

    def run_scan(self, detect_changes: bool = True) -> list[Change] | None:
        """
        Run a full scan and update inventory.

        Args:
            detect_changes: Whether to detect changes from previous inventory

        Returns:
            List of detected changes if detect_changes is True, None otherwise
        """
        if self.is_multi_repo:
            print("Scanning repositories:")
            print(f"  Core: {self.core_repo_path}")
            print(f"  Contrib: {self.repo_path}")
        else:
            print(f"Scanning repository: {self.repo_path}")

        # Load previous inventory if it exists
        old_inventory = None
        if detect_changes and self.inventory_manager.inventory_exists():
            old_inventory = self.inventory_manager.load_inventory()
            print("Loaded previous inventory for change detection")

        # Scan all components
        if self.is_multi_repo:
            inventory_data = self.scanner.scan_all_repos()
            components = inventory_data["components"]
        else:
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
        print(f"\nInventory saved to: {self.inventory_manager.inventory_dir}/")

        return changes

    def generate_docs(
        self,
        repo_owner: str = "open-telemetry",
        repo_name: str = "opentelemetry.io",
        fork_owner: str | None = None,
        base_branch: str = "main",
        local_path: str | None = None,
        dry_run: bool = False,
    ) -> dict | None:
        """
        Generate documentation pages and create a pull request.

        Args:
            repo_owner: Owner of the target repository
            repo_name: Name of the target repository
            fork_owner: Owner of the fork (defaults to authenticated user)
            base_branch: Base branch to target
            local_path: Local path to clone to (temporary if None)
            dry_run: If True, don't push or create PR

        Returns:
            PR metadata dict or None if failed
        """
        github_token = os.environ.get("GITHUB_TOKEN")
        if not github_token:
            print("\n❌ GITHUB_TOKEN environment variable not set", file=sys.stderr)
            return None

        print(f"\n📝 Generating documentation{' (DRY RUN)' if dry_run else ''}...")

        # Load current inventory
        inventory = self.inventory_manager.load_inventory()

        # Generate documentation pages
        doc_generator = DocGenerator(repository="opentelemetry-collector-contrib")
        output_dir = Path("content/en/docs/collector")
        pages = doc_generator.generate_all_pages(inventory, output_dir)

        print(f"  Generated {len(pages)} documentation page(s)")

        # Initialize PR creator
        pr_creator = PRCreator(
            github_token=github_token,
            repo_owner=repo_owner,
            repo_name=repo_name,
            fork_owner=fork_owner,
        )

        # Determine local path
        cleanup_local = False
        if local_path is None:
            local_path = Path(tempfile.mkdtemp(prefix="opentelemetry-io-"))
            cleanup_local = True
        else:
            local_path = Path(local_path)

        try:
            # Clone or update repository
            print(f"  Cloning/updating repository to {local_path}...")
            repo = pr_creator.clone_or_update_repo(local_path, base_branch)

            # Create feature branch
            branch_name = pr_creator.create_feature_branch(repo)
            print(f"  Created branch: {branch_name}")

            # Write generated pages
            file_paths = []
            for page_path, content in pages.items():
                full_path = local_path / page_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
                # Store relative path for git
                file_paths.append(str(Path(page_path)))

            # Commit changes
            # For now, we'll just say "refreshing documentation" since we don't have change tracking yet
            commit_msg = generate_commit_message([], [], [])
            has_changes = pr_creator.commit_changes(repo, file_paths, commit_msg)

            if not has_changes:
                print("  ✓ No changes to commit")
                return None

            print(f"  Committed changes to {branch_name}")

            # Push and create PR
            if not dry_run:
                print("  Pushing to fork...")
                pr_creator.push_to_fork(repo, branch_name)

                print("  Creating pull request...")
                pr_title = "docs: Update OpenTelemetry Collector component pages"
                pr_body_text = generate_pr_body([], [], [], [Path(p).name for p in file_paths])
                pr = pr_creator.create_pull_request(
                    title=pr_title,
                    body=pr_body_text,
                    head_branch=branch_name,
                    base_branch=base_branch,
                    dry_run=False,
                )

                if pr:
                    print(f"✅ Pull request created: {pr['url']}")
                    return pr
                else:
                    print("❌ Failed to create pull request")
                    return None
            else:
                print(f"  [DRY RUN] Would push branch: {branch_name}")
                print(f"  [DRY RUN] Would create PR to {repo_owner}/{repo_name}:{base_branch}")
                return {
                    "number": None,
                    "url": "DRY_RUN",
                    "title": "docs: Update OpenTelemetry Collector component pages",
                }

        finally:
            # Cleanup temporary directory if needed
            if cleanup_local and local_path.exists():
                pr_creator.cleanup_local_repo(local_path)


def main():
    """CLI entry point for the watcher."""
    if len(sys.argv) < 2:
        print(
            "Usage: python -m collector_watcher.runner <contrib_repo_path> [inventory_dir] [OPTIONS]"
        )
        print("\nOptions:")
        print("  --core-repo=PATH           Path to core collector repository (optional)")
        print("  --output-changes=FILE      Write changes to JSON file")
        print(
            "  --create-issues            Create GitHub issues for changes (requires GITHUB_TOKEN env var)"
        )
        print(
            "  --github-repo=REPO         GitHub repo for issues (default: jaydeluca/collector-watcher)"
        )
        print(
            "  --dry-run                  Don't actually create issues or PRs, just show what would be created"
        )
        print("\nDocumentation Generation Options:")
        print("  --generate-docs            Generate documentation pages and create PR")
        print("  --docs-repo=OWNER/REPO     Docs repo (default: open-telemetry/opentelemetry.io)")
        print("  --docs-fork-owner=OWNER    Fork owner (defaults to authenticated user)")
        print("  --docs-base-branch=BRANCH  Base branch (default: main)")
        print("  --docs-local-path=PATH     Local path for docs repo (temporary if not specified)")
        print("\nExamples:")
        print("  # Scan contrib repo only")
        print("  python -m collector_watcher.runner /path/to/opentelemetry-collector-contrib")
        print("\n  # Scan both core and contrib repos")
        print("  python -m collector_watcher.runner /path/to/contrib --core-repo=/path/to/core")
        print("\n  # Scan with options")
        print("  python -m collector_watcher.runner /path/to/repo --output-changes=changes.json")
        print("  python -m collector_watcher.runner /path/to/repo --create-issues --dry-run")
        print(
            "  python -m collector_watcher.runner /path/to/repo --core-repo=/path/to/core --generate-docs"
        )
        sys.exit(1)

    repo_path = sys.argv[1]
    inventory_dir = "data/inventory"
    core_repo_path = None
    output_changes_file = None
    create_issues = False
    github_repo = "jaydeluca/collector-watcher"
    dry_run = False
    generate_docs = False
    docs_repo = "open-telemetry/opentelemetry.io"
    docs_fork_owner = None
    docs_base_branch = "main"
    docs_local_path = None

    # Parse arguments
    for arg in sys.argv[2:]:
        if arg.startswith("--core-repo="):
            core_repo_path = arg.split("=", 1)[1]
        elif arg.startswith("--output-changes="):
            output_changes_file = arg.split("=", 1)[1]
        elif arg.startswith("--github-repo="):
            github_repo = arg.split("=", 1)[1]
        elif arg.startswith("--docs-repo="):
            docs_repo = arg.split("=", 1)[1]
        elif arg.startswith("--docs-fork-owner="):
            docs_fork_owner = arg.split("=", 1)[1]
        elif arg.startswith("--docs-base-branch="):
            docs_base_branch = arg.split("=", 1)[1]
        elif arg.startswith("--docs-local-path="):
            docs_local_path = arg.split("=", 1)[1]
        elif arg == "--create-issues":
            create_issues = True
        elif arg == "--generate-docs":
            generate_docs = True
        elif arg == "--dry-run":
            dry_run = True
        elif not arg.startswith("--"):
            inventory_dir = arg

    try:
        watcher = CollectorWatcher(repo_path, inventory_dir, core_repo_path=core_repo_path)
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

        # Generate documentation if requested
        if generate_docs:
            # Parse docs_repo into owner/name
            if "/" in docs_repo:
                docs_owner, docs_name = docs_repo.split("/", 1)
            else:
                print(
                    f"\n❌ Invalid docs-repo format: {docs_repo}. Expected: owner/repo",
                    file=sys.stderr,
                )
                sys.exit(1)

            watcher.generate_docs(
                repo_owner=docs_owner,
                repo_name=docs_name,
                fork_owner=docs_fork_owner,
                base_branch=docs_base_branch,
                local_path=docs_local_path,
                dry_run=dry_run,
            )

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
