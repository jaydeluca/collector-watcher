# Collector Watcher

Automated monitoring system for OpenTelemetry Collector components. Tracks changes across the core and contrib
repositories, maintains versioned inventory, and generates documentation tables for opentelemetry.io.

## Quick Start

The easiest way to run the full workflow locally:

```bash
./validate_workflow.sh
```

This will:
1. Clone/update collector repositories to `tmp_repos/`
2. Scan components and update inventory
3. Generate documentation updates (if `../opentelemetry.io` exists)
4. Show you what changed

**Custom paths:** Set environment variables if needed:
```bash
export CORE_REPO_PATH=/path/to/opentelemetry-collector
export CONTRIB_REPO_PATH=/path/to/opentelemetry-collector-contrib
export DOCS_REPO_PATH=/path/to/opentelemetry.io
./validate_workflow.sh
```

## Usage

### Scan Inventory

```bash
# Scan both repositories
collector-scan /path/to/contrib --core-repo=/path/to/core

# Check for new releases and update snapshots
collector-scan /path/to/contrib --core-repo=/path/to/core --mode=nightly
```

### Update Documentation

```bash
# Update docs in ../opentelemetry.io (uses latest version)
collector-docs

# Or specify a custom path and version
collector-docs --docs-repo=/path/to/opentelemetry.io --version=v0.140.1
```

**Version Handling:** The documentation generator automatically handles version mismatches between core and contrib distributions. If a specific version doesn't exist for a distribution, it falls back to the latest available version and displays a warning.

**Changelog Generation:** Automatically generates a summary of changes (new components, stability changes, distribution changes) when comparing versions.

## How It Works

**Inventory Management** (`collector_watcher`): Scans collector repositories to discover components, parses their
metadata, and stores versioned snapshots as YAML files.

**Documentation** (`docs_automation`): Generates markdown tables from inventory and updates opentelemetry.io pages
using marker-based replacement (only content between `<!-- BEGIN/END GENERATED -->` markers is modified).

**Changelog Generation** (`docs_automation`): Compares versions to produce human-readable summaries of component changes, including additions, removals, stability changes, and distribution changes.

## Inventory Format

Components are stored as `collector-metadata/{distribution}/{version}/{component_type}.yaml` with metadata including
stability levels, distributions, and component-specific details.

## Features

### Version Mismatch Handling

When generating documentation, if core and contrib are at different versions (e.g., contrib at v0.140.1, core at v0.140.0), the system automatically:

1. Detects the version mismatch
2. Falls back to the latest available version for each distribution
3. Displays a clear warning message
4. Merges components correctly without losing data

See [BUGFIX_VERSION_MISMATCH.md](BUGFIX_VERSION_MISMATCH.md) for detailed information.

### Automated Changelog

Automatically generates summaries showing:
- **New components** added between versions
- **Removed components**
- **Stability changes** (e.g., alpha → beta → stable)
- **Distribution changes** (e.g., added to K8s distribution)

Example output:
```markdown
## Summary of Changes

### Receivers

**New components:**
- `newreceiver`

**Stability changes:**
- `otlpreceiver`: traces: alpha → beta
```

## Development

Install [uv](https://docs.astral.sh/uv/) for dependency management:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

Run tests and linting:

```bash
uv run pytest tests/ --cov=src
uv run ruff check src/ tests/

# fix them
uv run ruff format --check src/ tests/
```

### Running Specific Tests

```bash
# Test version fallback
uv run pytest tests/docs_automation/test_update_docs.py -v

# Test changelog generation
uv run pytest tests/docs_automation/test_changelog_generator.py -v

# Test all
uv run pytest -v
```
