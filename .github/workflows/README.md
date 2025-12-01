# GitHub Actions Workflows

## update-docs.yml

Nightly workflow that scans collector repositories, generates component documentation, and creates PRs.

**Runs:** Daily at 3 AM UTC (or manual trigger)

### Required Setup

**Secrets** (`Settings > Secrets and variables > Actions`):
- `PAT_TOKEN`: Personal Access Token with `repo` and `pull_request` permissions
- `DOCS_REPO_OWNER` (optional): Your GitHub username (defaults to repo owner)

### Manual Trigger

**Actions** tab → **"Update OpenTelemetry.io Documentation"** → **"Run workflow"**

Optional inputs:
- `version`: Specific version (e.g., `v0.140.1`) or leave empty for latest
- `target_repo_owner`: `jaydeluca` (default, targets fork) or `open-telemetry` (upstream)

### Behavior

**Fork mode** (default):
- Syncs fork with upstream before creating branch
- Ensures PRs only contain doc changes (no upstream commits/contributors)

**Upstream mode** (`target_repo_owner: open-telemetry`):
- Skips fork sync
- Creates PR directly against upstream
