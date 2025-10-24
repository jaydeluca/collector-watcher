#!/usr/bin/env python3
"""
Generate documentation pages locally for testing.

This script generates OpenTelemetry Collector component documentation pages
and writes them directly to your local opentelemetry.io repository for
preview and testing.

Usage:
    1. First scan repositories to update inventory:
       uv run python -m collector_watcher.runner /path/to/contrib --core-repo=/path/to/core

    2. Generate documentation pages:
       uv run python generate_docs_local.py [--distribution=contrib] [--version=v0.138.0]

    3. Preview the documentation:
       cd /Users/jaydeluca/code/projects/opentelemetry.io
       hugo server
       # Open http://localhost:1313/docs/collector/components/
"""

import sys
from pathlib import Path

from src.collector_watcher.doc_generator import DocGenerator
from src.collector_watcher.inventory import InventoryManager
from src.collector_watcher.version_detector import Version


def main():
    """Generate docs to local opentelemetry.io repository."""
    # Parse arguments
    distribution = "contrib"
    version_str = None
    
    for arg in sys.argv[1:]:
        if arg.startswith("--distribution="):
            distribution = arg.split("=", 1)[1]
        elif arg.startswith("--version="):
            version_str = arg.split("=", 1)[1]
    
    # Load inventory
    print(f"Loading inventory for {distribution}...")
    inv_mgr = InventoryManager("collector-metadata")
    
    # Determine which version to use
    if version_str:
        version = Version.from_string(version_str)
    else:
        # Use the latest non-snapshot version
        versions = inv_mgr.list_versions(distribution)
        if not versions:
            print(f"❌ No versions found for {distribution}")
            sys.exit(1)
        
        # Filter out snapshots and get the latest
        release_versions = [v for v in versions if not v.is_snapshot]
        if not release_versions:
            print(f"❌ No release versions found for {distribution}")
            sys.exit(1)
        
        version = release_versions[0]
    
    print(f"Using version: {version}")
    inventory_data = inv_mgr.load_versioned_inventory(distribution, version)
    
    # Convert to legacy format for doc generator
    inventory = {
        "repository": inventory_data.get("repository", ""),
        "components": inventory_data.get("components", {})
    }

    total_components = sum(len(comps) for comps in inventory["components"].values())
    print(f"Loaded {total_components} components")

    # Generate pages
    print("\nGenerating documentation pages...")
    doc_gen = DocGenerator(repository="opentelemetry-collector-contrib")
    output_dir = Path("content/en/docs/collector")
    pages = doc_gen.generate_all_pages(inventory, output_dir)

    print(f"Generated {len(pages)} pages")

    # Write to local opentelemetry.io repo
    docs_repo = Path("../opentelemetry.io")

    if not docs_repo.exists():
        print(f"\n❌ Error: {docs_repo} does not exist")
        return

    print(f"\nWriting pages to {docs_repo}...")
    for page_path, content in pages.items():
        full_path = docs_repo / page_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        print(f"  ✓ {page_path}")

    print(f"\n✅ Done! Pages written to {docs_repo / output_dir / 'components'}")
    print("\nTo view the pages:")
    print(f"  cd {docs_repo}")
    print("  hugo server")
    print("  Open http://localhost:1313/docs/collector/components/")


if __name__ == "__main__":
    main()
