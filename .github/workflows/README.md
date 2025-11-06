# GitHub Actions Workflows

## Monitor Workflow (`monitor.yml`)

Scans OpenTelemetry Collector repositories for changes and updates inventory.

**What it does:**
1. Clones opentelemetry-collector and opentelemetry-collector-contrib
2. Runs versioned inventory scan (nightly mode)
3. Detects new releases and updates snapshots
4. Creates/updates PR with inventory changes

**Setup:**
- Optional: Set `PAT_TOKEN` secret for better rate limits
- Falls back to default GITHUB_TOKEN if not set

## Update Documentation Workflow (`update-docs.yml`)

Generates documentation tables for opentelemetry.io and creates PRs directly to upstream.

**Triggers:**
- Nightly at 3 AM UTC (scheduled)
- Manual via workflow_dispatch
  - Optional: Specify version to generate docs for

**What it does:**
1. Clones **upstream** opentelemetry.io (always up-to-date, no sync issues)
2. Scans collector repositories for latest component metadata
3. Generates markdown tables for receiver, processor, exporter, connector, and extension pages
4. Runs formatting (npm run fix:format)
5. Commits changes and pushes branch to your fork
6. Creates PR **directly to upstream** open-telemetry/opentelemetry.io if changes detected

**Setup Required:**

#### Step 1: Fork opentelemetry.io

1. Go to https://github.com/open-telemetry/opentelemetry.io
2. Click "Fork" to create your fork
3. Note your fork URL: `https://github.com/YOUR_USERNAME/opentelemetry.io`

#### Step 2: Create Personal Access Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a descriptive name: "collector-watcher-docs"
4. Select these scopes:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `workflow` (Update GitHub Action workflows)

#### Step 3: Add Secrets to Repository

1. Go to your collector-watcher repository
2. Click Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add these secrets:

   **PAT_TOKEN** (required)
   - Name: `PAT_TOKEN`
   - Value: Your personal access token from Step 2

   **DOCS_REPO_OWNER** (optional)
   - Name: `DOCS_REPO_OWNER`
   - Value: Your GitHub username (the owner of your opentelemetry.io fork)
   - If not set, defaults to the collector-watcher repository owner
