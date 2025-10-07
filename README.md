# Collector Watcher

Automated monitoring system for OpenTelemetry Collector components. Tracks changes in component structure and metadata
across both the opentelemetry-collector (core) and opentelemetry-collector-contrib repositories.

## Overview

Collector Watcher scans OpenTelemetry Collector components and maintains an inventory. When run, it:
- Discovers all collector components (connectors, exporters, extensions, processors, receivers)
- Scans both core and contrib repositories and merges component data
- Parses component metadata from metadata.yaml files
- Maintains inventory in YAML format
- Generates documentation pages for opentelemetry.io
- Changes are detected via git diff of the inventory files

## Usage

### Basic Scan

Run a scan of the collector-contrib repository only:

```bash
uv run python -m collector_watcher.runner /path/to/opentelemetry-collector-contrib
```

Or scan both core and contrib repositories (recommended):

```bash
uv run python -m collector_watcher.runner /path/to/opentelemetry-collector-contrib --core-repo=/path/to/opentelemetry-collector
```

After scanning, use `git diff data/inventory/` to see what changed in the inventory.

### Generate Documentation

Generate documentation pages and create a PR to opentelemetry.io:

```bash
uv run python -m collector_watcher.runner /path/to/contrib --core-repo=/path/to/core --generate-docs --docs-repo=owner/repo
```

### Local Documentation Testing

For local testing without creating PRs:

```bash
# 1. First scan repositories to update inventory
uv run python -m collector_watcher.runner /path/to/contrib --core-repo=/path/to/core

# 2. Generate documentation pages locally
uv run python generate_docs_local.py

# 3. Preview the documentation
cd /path/to/opentelemetry.io
hugo server
# Open http://localhost:1313/docs/collector/components/
```

## Development

### Prerequisites

Install uv (recommended for Python dependency management):
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

### Setup

```bash
# Clone the repository
cd /path/to/collector-watcher

# Install dependencies
uv sync
```

### Running Tests

```bash
# Run all tests
uv run pytest tests/

# Run with coverage
uv run pytest tests/ --cov=src/collector_watcher

# Run linter
uv run ruff check src/ tests/

# Run formatter
uv run ruff format src/ tests/
```

## Inventory Format

The inventory is stored as separate YAML files per component type in `data/inventory/`:

```
data/inventory/
├── connector.yaml
├── exporter.yaml
├── extension.yaml
├── processor.yaml
└── receiver.yaml
```

Each file contains:

```yaml
repository: opentelemetry-collector-contrib
component_type: receiver
components:
  - name: otlpreceiver
    metadata:
      type: otlp
      status:
        stability:
          stable: [metrics, traces]
```

Timestamps and commit SHAs are intentionally excluded so files only change when component metadata or existence changes, making git diffs meaningful. Splitting by component type keeps file sizes manageable.

## GitHub Actions

### CI Workflow
Runs on all pull requests:
- Linting with ruff
- Code formatting checks
- Type checking with mypy
- Test suite with coverage reporting

### Monitoring Workflow
Runs daily to monitor both core and contrib repositories:
- Scans both opentelemetry-collector and opentelemetry-collector-contrib
- Merges component data into inventory files
- Opens PR with updated inventory files if changes detected
- Changes are visible via git diff in the PR