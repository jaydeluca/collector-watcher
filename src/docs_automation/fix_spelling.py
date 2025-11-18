#!/usr/bin/env python3
"""
Fix spelling errors by updating cSpell:ignore in markdown front matter.

This script runs cspell to detect spelling errors in generated documentation,
identifies component names, and updates the cSpell:ignore line in the YAML
front matter of each affected file.
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set


def run_cspell(docs_repo_path: Path) -> Dict[str, List[str]]:
    """
    Run cspell on collector component documentation.

    Args:
        docs_repo_path: Path to opentelemetry.io repository

    Returns:
        Dictionary mapping file paths to lists of misspelled words
    """
    component_docs = docs_repo_path / "content/en/docs/collector/components"

    # Run cspell
    cmd = [
        "npx",
        "cspell",
        "--no-progress",
        "-c",
        str(docs_repo_path / ".cspell.yml"),
        str(component_docs / "*.md"),
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=docs_repo_path,
            capture_output=True,
            text=True,
            check=False,  # Don't raise on non-zero exit (spelling errors)
        )

        # Parse cspell output to extract misspelled words
        # cspell output format: "filename:line:col - Unknown word (word)"
        misspellings: Dict[str, List[str]] = {}
        pattern = r"^(.+?):(\d+):(\d+)\s+-\s+Unknown word \((.+?)\)"

        for line in result.stdout.split("\n"):
            match = re.match(pattern, line)
            if match:
                filepath = match.group(1)
                word = match.group(4)

                if filepath not in misspellings:
                    misspellings[filepath] = []
                misspellings[filepath].append(word)

        return misspellings

    except FileNotFoundError:
        print("Error: npx not found. Make sure Node.js is installed.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error running cspell: {e}", file=sys.stderr)
        sys.exit(1)


def load_component_names(inventory_path: Path) -> Set[str]:
    """
    Load all component names from the inventory.

    Args:
        inventory_path: Path to collector-metadata directory

    Returns:
        Set of all component names
    """
    import yaml

    component_names = set()

    # Find all component YAML files (use the latest version)
    for dist_dir in inventory_path.iterdir():
        if not dist_dir.is_dir():
            continue

        # Get latest version directory (excluding snapshots)
        versions = sorted(
            [v for v in dist_dir.iterdir() if v.is_dir() and "SNAPSHOT" not in v.name],
            reverse=True,
        )
        if not versions:
            continue

        latest_version = versions[0]

        # Read all component files
        for component_file in latest_version.glob("*.yaml"):
            with open(component_file) as f:
                data = yaml.safe_load(f)
                components = data.get("components", [])
                for comp in components:
                    name = comp.get("name")
                    if name:
                        component_names.add(name)

    return component_names


def update_frontmatter_ignore_list(file_path: Path, new_words: Set[str]) -> bool:
    """
    Update the cSpell:ignore line in the markdown front matter.

    Args:
        file_path: Path to markdown file
        new_words: Words to add to ignore list

    Returns:
        True if file was modified
    """
    with open(file_path) as f:
        content = f.read()

    # Match front matter (between --- delimiters)
    frontmatter_pattern = r"^---\n(.*?)\n---\n"
    match = re.match(frontmatter_pattern, content, re.DOTALL)

    if not match:
        print(f"  ⚠️  No front matter found in {file_path.name}")
        return False

    frontmatter = match.group(1)
    frontmatter_end = match.end()

    # Find cSpell:ignore line
    cspell_pattern = r"cSpell:ignore:\s*(.+)"
    cspell_match = re.search(cspell_pattern, frontmatter)

    if cspell_match:
        # Parse existing words
        existing_words_str = cspell_match.group(1).strip()
        existing_words = set(existing_words_str.split())

        # Combine and sort
        all_words = existing_words | new_words
        sorted_words = sorted(all_words, key=str.lower)

        # Replace the line
        new_cspell_line = f"cSpell:ignore: {' '.join(sorted_words)}"
        new_frontmatter = frontmatter.replace(cspell_match.group(0), new_cspell_line)
    else:
        # Add new cSpell:ignore line before the closing ---
        sorted_words = sorted(new_words, key=str.lower)
        new_cspell_line = f"cSpell:ignore: {' '.join(sorted_words)}"

        # Add the line at the end of frontmatter (before the closing ---)
        new_frontmatter = frontmatter + f"\n{new_cspell_line}"

    # Reconstruct the content
    new_content = f"---\n{new_frontmatter}\n---\n" + content[frontmatter_end:]

    # Write back
    with open(file_path, "w") as f:
        f.write(new_content)

    return True


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python fix_spelling.py <docs_repo_path>")
        sys.exit(1)

    docs_repo_path = Path(sys.argv[1])
    if not docs_repo_path.exists():
        print(f"Error: {docs_repo_path} does not exist", file=sys.stderr)
        sys.exit(1)

    collector_watcher_path = Path(__file__).parent.parent.parent
    inventory_path = collector_watcher_path / "collector-metadata"

    print("Running cspell to detect spelling errors...")
    misspellings = run_cspell(docs_repo_path)

    if not misspellings:
        print("✓ No spelling errors found!")
        return

    print(f"Found spelling errors in {len(misspellings)} file(s)")

    # Load component names
    print("\nLoading component names from inventory...")
    component_names = load_component_names(inventory_path)
    print(f"Loaded {len(component_names)} component names")

    # Process each file
    files_updated = 0
    total_words_added = 0

    for filepath, words in misspellings.items():
        # Convert to Path and get relative path
        file_path = Path(filepath)
        if not file_path.exists():
            # Try making it relative to docs repo
            file_path = docs_repo_path / filepath

        if not file_path.exists():
            print(f"  ⚠️  File not found: {filepath}")
            continue

        # Filter to only component names
        component_words = set(words) & component_names

        if not component_words:
            print(f"\n{file_path.name}:")
            print(f"  ⚠️  No component names found in spelling errors")
            print(f"  Words: {', '.join(sorted(set(words)))}")
            continue

        print(f"\n{file_path.name}:")
        print(f"  Adding {len(component_words)} words: {', '.join(sorted(component_words))}")

        # Update the file
        if update_frontmatter_ignore_list(file_path, component_words):
            files_updated += 1
            total_words_added += len(component_words)

    # Summary
    if files_updated > 0:
        print(f"\n✓ Updated {files_updated} file(s), added {total_words_added} words total")

        # Run cspell again to verify
        print("\nVerifying spelling errors are fixed...")
        remaining = run_cspell(docs_repo_path)

        if remaining:
            remaining_count = sum(len(words) for words in remaining.values())
            print(f"\n⚠️  {remaining_count} spelling errors remain in {len(remaining)} file(s)")
            print("These may be legitimate typos or non-component words.")
        else:
            print("✓ All component name spelling errors fixed!")
    else:
        print("\n⚠️  No files were updated")


if __name__ == "__main__":
    main()
