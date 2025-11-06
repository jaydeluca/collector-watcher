# Collector Watcher

Automated monitoring system for OpenTelemetry Collector components. Tracks changes in component structure and metadata
across both the opentelemetry-collector (core) and opentelemetry-collector-contrib repositories.

## What It Does

Collector Watcher scans OpenTelemetry Collector repositories and:
- Discovers components (receivers, processors, exporters, connectors, extensions)
- Tracks component metadata across versions
- Maintains versioned inventory in YAML format
- Generates documentation tables for opentelemetry.io

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

## Project Structure

```
collector-watcher/
├── src/
│   ├── collector_watcher/          # Inventory management
│   │   ├── scanner.py              # Component discovery
│   │   ├── multi_repo_scanner.py   # Scan core + contrib
│   │   ├── parser.py               # Parse metadata.yaml files
│   │   ├── inventory.py            # Versioned storage
│   │   ├── version_detector.py     # Git tag parsing
│   │   └── scan_inventory.py       # CLI entry point
│   └── docs_automation/            # Documentation generation
│       ├── doc_generator.py        # Generate markdown tables
│       ├── doc_updater.py          # Update existing pages
│       └── update_docs.py          # CLI entry point
├── tests/                          # Test suites
│   ├── collector_watcher/
│   └── docs_automation/
├── collector-metadata/             # Versioned inventory
│   ├── core/
│   │   ├── v0.112.0/
│   │   └── v0.113.0-SNAPSHOT/
│   └── contrib/
│       └── ...
└── tmp_repos/                      # Cloned upstream repos (gitignored)
```

## Module Overview

### Inventory Management (`collector_watcher`)

- **scanner.py** - Finds components by scanning directories for go.mod files
- **multi_repo_scanner.py** - Coordinates scanning core and contrib repositories
- **parser.py** - Extracts metadata from component metadata.yaml files
- **inventory.py** - Saves/loads versioned inventory to YAML files
- **version_detector.py** - Detects versions from git tags (handles releases and snapshots)
- **scan_inventory.py** - CLI entry point (`collector-scan` command)

### Documentation (`docs_automation`)

- **doc_generator.py** - Generates markdown tables from inventory
- **doc_updater.py** - Updates content between HTML comment markers
- **update_docs.py** - CLI entry point (`collector-docs` command)

Documentation uses marker-based updates: only content between
`<!-- BEGIN GENERATED: X -->` and `<!-- END GENERATED: X -->` markers is modified, preserving all manual content.

## Inventory Format

Components are tracked in versioned YAML files:

```
collector-metadata/{distribution}/{version}/{component_type}.yaml
```

Example structure:
```yaml
distribution: contrib
version: v0.113.0
repository: opentelemetry-collector-contrib
component_type: receiver
components:
  - name: otlpreceiver
    metadata:
      status:
        distributions: [core, contrib]
        stability:
          stable: [traces, metrics, logs]
```

## Development

### Setup

Install [uv](https://docs.astral.sh/uv/) for dependency management:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync  # Install dependencies
```

### Testing

```bash
# Run tests
uv run pytest tests/

# With coverage
uv run pytest tests/ --cov=src

# Lint and format
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```
