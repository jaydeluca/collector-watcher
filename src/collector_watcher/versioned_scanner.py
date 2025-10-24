"""Versioned scanner for OpenTelemetry Collector repositories."""

from typing import Any

from .inventory import DistributionName, InventoryManager
from .scanner import ComponentScanner
from .version_detector import Version, VersionDetector

DistributionConfig = dict[DistributionName, str]


class VersionedScanner:
    """
    Scans collector repositories with version awareness.

    Handles:
    - Detecting latest release versions
    - Scanning specific version tags
    - Creating SNAPSHOT versions from main branch
    - Cleaning up old snapshots
    """

    def __init__(
        self,
        repos: DistributionConfig,
        inventory_manager: InventoryManager,
    ):
        """
        Initialize the versioned scanner.

        Args:
            repos: Dict mapping distribution name to local repo path
                   e.g., {"core": "/path/to/collector", "contrib": "/path/to/collector-contrib"}
            inventory_manager: InventoryManager instance for saving results
        """
        self.repos = repos
        self.inventory_manager = inventory_manager
        self.version_detectors = {dist: VersionDetector(path) for dist, path in repos.items()}

    def get_repository_name(self, distribution: DistributionName) -> str:
        """
        Get the canonical repository name for a distribution.

        Args:
            distribution: Distribution name

        Returns:
            Repository name
        """
        if distribution == "core":
            return "opentelemetry-collector"
        elif distribution == "contrib":
            return "opentelemetry-collector-contrib"
        else:
            return f"opentelemetry-collector-{distribution}"

    def scan_version(
        self,
        distribution: DistributionName,
        version: Version,
        checkout: bool = True,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Scan a specific version of a distribution.

        Args:
            distribution: Distribution name
            version: Version to scan
            checkout: Whether to checkout the version tag (default: True)

        Returns:
            Dictionary of component type to component list
        """
        repo_path = self.repos[distribution]
        detector = self.version_detectors[distribution]

        # Checkout the version if requested
        if checkout and not version.is_snapshot:
            print(f"  Checking out {distribution} {version}...")
            detector.checkout_version(version)
        elif checkout and version.is_snapshot:
            print(f"  Checking out {distribution} main branch...")
            detector.checkout_main()

        # Scan components
        print(f"  Scanning {distribution} {version}...")
        scanner = ComponentScanner(repo_path)
        components = scanner.scan_all_components()

        # Print summary
        total = sum(len(comps) for comps in components.values())
        print(f"    Found {total} components")

        return components

    def save_version(
        self,
        distribution: DistributionName,
        version: Version,
        components: dict[str, list[dict[str, Any]]],
    ) -> None:
        """
        Save scanned components for a specific version.

        Args:
            distribution: Distribution name
            version: Version being saved
            components: Scanned components
        """
        repository = self.get_repository_name(distribution)
        self.inventory_manager.save_versioned_inventory(
            distribution=distribution,
            version=version,
            components=components,
            repository=repository,
        )
        print(f"  Saved {distribution} {version}")

    def process_latest_release(self, distribution: DistributionName) -> Version | None:
        """
        Process the latest release version if not already tracked.

        Args:
            distribution: Distribution name

        Returns:
            Latest version if processed, None if already exists or no releases
        """
        detector = self.version_detectors[distribution]

        # Get latest release
        latest = detector.get_latest_release_tag()
        if latest is None:
            print(f"No releases found for {distribution}")
            return None

        # Check if already tracked
        if self.inventory_manager.version_exists(distribution, latest):
            print(f"Version {distribution} {latest} already tracked")
            return None

        print(f"\nProcessing new release: {distribution} {latest}")

        # Scan the version
        components = self.scan_version(distribution, latest, checkout=True)

        # Save the inventory
        self.save_version(distribution, latest, components)

        return latest

    def update_snapshot(self, distribution: DistributionName) -> Version:
        """
        Update or create the SNAPSHOT version for a distribution.

        This:
        1. Cleans up old snapshots
        2. Determines next snapshot version
        3. Scans main branch
        4. Saves as new snapshot

        Args:
            distribution: Distribution name

        Returns:
            Snapshot version that was created
        """
        detector = self.version_detectors[distribution]

        # Cleanup old snapshots
        print(f"\nCleaning up old {distribution} snapshots...")
        removed = self.inventory_manager.cleanup_snapshots(distribution)
        if removed > 0:
            print(f"  Removed {removed} old snapshot(s)")

        # Determine next snapshot version
        snapshot_version = detector.determine_next_snapshot_version()
        print(f"\nUpdating {distribution} {snapshot_version}...")

        # Scan main branch
        components = self.scan_version(distribution, snapshot_version, checkout=True)

        # Save snapshot
        self.save_version(distribution, snapshot_version, components)

        return snapshot_version

    def run_nightly_scan(self) -> dict[str, Any]:
        """
        Run the nightly scan workflow.

        This performs the complete workflow:
        1. Check for new releases in each distribution
        2. Process any new releases
        3. Update snapshots for each distribution

        Returns:
            Summary of what was processed
        """
        summary = {
            "new_releases": [],
            "snapshots_updated": [],
        }

        print("=" * 60)
        print("NIGHTLY SCAN")
        print("=" * 60)

        # Process each distribution
        for distribution in self.repos.keys():
            print(f"\n{'=' * 60}")
            print(f"Distribution: {distribution.upper()}")
            print(f"{'=' * 60}")

            # Process latest release
            latest = self.process_latest_release(distribution)
            if latest:
                summary["new_releases"].append(
                    {"distribution": distribution, "version": str(latest)}
                )

            # Update snapshot
            snapshot = self.update_snapshot(distribution)
            summary["snapshots_updated"].append(
                {"distribution": distribution, "version": str(snapshot)}
            )

        # Final summary
        print(f"\n{'=' * 60}")
        print("SCAN COMPLETE")
        print(f"{'=' * 60}")
        print(f"New releases processed: {len(summary['new_releases'])}")
        for item in summary["new_releases"]:
            print(f"  - {item['distribution']}: {item['version']}")
        print(f"Snapshots updated: {len(summary['snapshots_updated'])}")
        for item in summary["snapshots_updated"]:
            print(f"  - {item['distribution']}: {item['version']}")

        return summary

    def scan_specific_version(
        self,
        distribution: DistributionName,
        version: Version,
        force: bool = False,
    ) -> None:
        """
        Scan and save a specific version.

        Args:
            distribution: Distribution name
            version: Version to scan
            force: If True, rescan even if version already exists
        """
        # Check if already exists
        if not force and self.inventory_manager.version_exists(distribution, version):
            print(f"Version {distribution} {version} already exists (use --force to rescan)")
            return

        print(f"\nScanning {distribution} {version}...")

        # Scan the version
        components = self.scan_version(distribution, version, checkout=True)

        # Save the inventory
        self.save_version(distribution, version, components)
