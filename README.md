# Collector Watcher

Automated monitoring system for OpenTelemetry Collector components. Tracks changes in component structure and metadata
across the opentelemetry-collector-contrib repository.

## Overview

Collector Watcher scans OpenTelemetry Collector components and detects changes in their metadata. When run, it:
- Discovers all collector components (connectors, exporters, extensions, processors, receivers)
- Parses component metadata from metadata.yaml files
- Detects changes from previous scans
- Optionally creates GitHub issues for detected changes
- Maintains historical inventory in YAML format

## Usage

### Basic Scan

Run a scan of the collector-contrib repository:

```bash
uv run python -m collector_watcher.runner /path/to/opentelemetry-collector-contrib
```

### Export Changes

Export detected changes to JSON:

```bash
uv run python -m collector_watcher.runner /path/to/repo --output-changes=changes.json
```

### Create GitHub Issues

Create GitHub issues for detected changes (requires `GITHUB_TOKEN` environment variable):

```bash
# Dry-run mode (test without creating issues)
export GITHUB_TOKEN=your_token
uv run python -m collector_watcher.runner /path/to/repo --create-issues --dry-run

# Create issues for real
uv run python -m collector_watcher.runner /path/to/repo --create-issues --github-repo=owner/repo
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
Runs daily to monitor collector-contrib repository:
- Scans opentelemetry-collector-contrib for changes
- Creates GitHub issues for detected changes
- Opens PR with updated inventory files if changes detected