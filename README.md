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
# Update docs in ../opentelemetry.io
collector-docs

# Or specify a custom path
collector-docs --docs-repo=/path/to/opentelemetry.io
```

## How It Works

**Inventory Management** (`collector_watcher`): Scans collector repositories to discover components, parses their
metadata, and stores versioned snapshots as YAML files.

**Documentation** (`docs_automation`): Generates markdown tables from inventory and updates opentelemetry.io pages
using marker-based replacement (only content between `<!-- BEGIN/END GENERATED -->` markers is modified).

## Inventory Format

Components are stored as `collector-metadata/{distribution}/{version}/{component_type}.yaml` with metadata including
stability levels, distributions, and component-specific details.

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
