# Collector Watcher

Automated monitoring system for OpenTelemetry Collector components. Tracks changes in component structure and metadata
across both the opentelemetry-collector (core) and opentelemetry-collector-contrib repositories on a **versioned basis**.

## Overview

Collector Watcher scans OpenTelemetry Collector components and maintains a versioned inventory. When run, it:
- Discovers all collector components (connectors, exporters, extensions, processors, receivers)
- Tracks components separately by distribution (core, contrib) and version
- Parses component metadata from metadata.yaml files
- Maintains versioned inventory in YAML format at `collector-metadata/{distribution}/{version}/`
- Tracks finalized release versions and current SNAPSHOT from main branch
- Generates documentation pages for opentelemetry.io
- Changes are detected via git diff of the versioned inventory files

## Usage

### Nightly Scan (Recommended)

Run the full nightly workflow that checks for new releases and updates snapshots:

```bash
uv run python -m collector_watcher.runner /path/to/opentelemetry-collector-contrib --core-repo=/path/to/opentelemetry-collector
```

This will:
1. Check for new release versions in both repositories
2. Scan and save any new releases found
3. Update SNAPSHOT versions from the main branch
4. Clean up old SNAPSHOT directories

After scanning, use `git diff collector-metadata/` to see what changed.

### Update Snapshots Only

To only update the SNAPSHOT versions without checking for new releases:

```bash
uv run python -m collector_watcher.runner /path/to/opentelemetry-collector-contrib --core-repo=/path/to/opentelemetry-collector --mode=snapshot
```

### Check for New Releases Only

To only check for and process new releases:

```bash
uv run python -m collector_watcher.runner /path/to/opentelemetry-collector-contrib --core-repo=/path/to/opentelemetry-collector --mode=release
```

### Scan a Specific Version

To scan a specific version (useful for backfilling historical data):

```bash
uv run python -m collector_watcher.runner /path/to/opentelemetry-collector-contrib --core-repo=/path/to/opentelemetry-collector --mode=specific --version=v0.112.0
```

### Legacy Mode

To use the old (non-versioned) scanning behavior:

```bash
uv run python -m collector_watcher.runner /path/to/opentelemetry-collector-contrib --legacy
```

### Generate Documentation

Generate documentation pages and create a PR to opentelemetry.io:

```bash
uv run python -m collector_watcher.runner /path/to/contrib --core-repo=/path/to/core --generate-docs --docs-repo=owner/repo
```

### Local Documentation Testing

For local testing without creating PRs. The documentation generator uses a **marker-based update system** that preserves manual content while updating auto-generated sections:

```bash
# 1. First scan repositories to update inventory
uv run python -m collector_watcher.runner /path/to/contrib --core-repo=/path/to/core

# 2. Update documentation tables in existing pages (preserves manual content)
uv run python generate_docs_local.py

# 3. Or specify a custom docs repo path
uv run python generate_docs_local.py --docs-repo=/path/to/opentelemetry.io

# 4. Or use a specific version
uv run python generate_docs_local.py --version=v0.138.0

# 5. Preview the documentation
cd /path/to/opentelemetry.io
hugo server
# Open http://localhost:1313/docs/collector/components/
```

**Marker-Based Updates:** The generator only updates sections marked with HTML comment markers like `<!-- BEGIN GENERATED: receiver-table -->` and `<!-- END GENERATED: receiver-table -->`, preserving all manual content outside these markers. See `templates/README.md` for details.

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

The inventory is stored in a versioned directory structure:

```
collector-metadata/
├── core/
│   ├── v0.112.0/
│   │   ├── connector.yaml
│   │   ├── exporter.yaml
│   │   ├── extension.yaml
│   │   ├── processor.yaml
│   │   └── receiver.yaml
│   ├── v0.113.0/
│   │   └── ...
│   └── v0.114.0-SNAPSHOT/
│       └── ...
└── contrib/
    ├── v0.112.0/
    │   └── ...
    ├── v0.113.0/
    │   └── ...
    └── v0.114.0-SNAPSHOT/
        └── ...
```

Each version directory contains separate YAML files per component type. Each file contains:

```yaml
distribution: contrib
version: v0.113.0
repository: opentelemetry-collector-contrib
component_type: receiver
components:
  - name: otlpreceiver
    metadata:
      type: otlp
      status:
        distributions: [core, contrib]  # Which distributions include this component
        stability:
          stable: [metrics, traces]
```

Key principles:
- **Distributions are tracked separately**: Core and contrib each have their own version directories
- **Only finalized releases are tracked permanently**: Each release tag gets its own directory
- **Only ONE snapshot exists at a time**: The latest `-SNAPSHOT` version representing the main branch
- **Timestamps excluded**: Files only change when component metadata or existence changes, making git diffs meaningful
- **Distribution metadata**: Components specify which distributions (core, contrib, k8s, etc.) include them

## GitHub Actions

### CI Workflow
Runs on all pull requests:
- Linting with ruff
- Code formatting checks
- Type checking with mypy
- Test suite with coverage reporting

### Monitoring Workflow
Runs daily to monitor both core and contrib repositories:
- Checks for new release versions in both repositories
- Scans and saves any new releases found
- Updates SNAPSHOT versions from main branch
- Cleans up old SNAPSHOT directories
- Opens PR with updated versioned inventory files if changes detected
- Changes are visible via git diff in the PR showing new/updated version directories