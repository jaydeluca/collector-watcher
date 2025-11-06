#!/bin/bash
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Default paths (can be overridden)
# By default, use tmp_repos within this project to avoid touching forks
TMP_REPOS_DIR="${TMP_REPOS_DIR:-${SCRIPT_DIR}/tmp_repos}"
CORE_REPO_PATH="${CORE_REPO_PATH:-${TMP_REPOS_DIR}/opentelemetry-collector}"
CONTRIB_REPO_PATH="${CONTRIB_REPO_PATH:-${TMP_REPOS_DIR}/opentelemetry-collector-contrib}"

# Docs repo defaults to sibling directory (fork)
DOCS_REPO_PATH="${DOCS_REPO_PATH:-${SCRIPT_DIR}/../opentelemetry.io}"

mkdir -p "$TMP_REPOS_DIR"

echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}Collector Watcher - End-to-End Validation${NC}"
echo -e "${BLUE}===========================================${NC}"
echo ""
echo "Working directory: ${SCRIPT_DIR}"
echo "Repositories will be cloned to: ${TMP_REPOS_DIR}"
echo ""

# Function to clone or update a repo
clone_or_update_repo() {
    local repo_url=$1
    local repo_path=$2
    local repo_name=$3

    if [ -d "$repo_path/.git" ]; then
        echo -e "${YELLOW}Updating $repo_name...${NC}"
        cd "$repo_path"
        # Clean any local changes and fetch latest
        git reset --hard HEAD
        git clean -fd
        git fetch origin
        git fetch --tags
        # Reset to latest main without requiring merge
        git reset --hard origin/main
        cd - > /dev/null
        echo -e "${GREEN}✓ $repo_name updated${NC}"
    else
        echo -e "${YELLOW}Cloning $repo_name...${NC}"
        git clone "$repo_url" "$repo_path"
        cd "$repo_path"
        git fetch --tags
        cd - > /dev/null
        echo -e "${GREEN}✓ $repo_name cloned${NC}"
    fi
    echo ""
}

echo -e "${BLUE}Step 1: Cloning/Updating Upstream Repositories${NC}"
echo "These will be cloned from official upstream (not forks):"
echo "  Core: $CORE_REPO_PATH"
echo "  Contrib: $CONTRIB_REPO_PATH"
echo ""

clone_or_update_repo \
    "https://github.com/open-telemetry/opentelemetry-collector.git" \
    "$CORE_REPO_PATH" \
    "opentelemetry-collector (core)"

clone_or_update_repo \
    "https://github.com/open-telemetry/opentelemetry-collector-contrib.git" \
    "$CONTRIB_REPO_PATH" \
    "opentelemetry-collector-contrib"

echo -e "${BLUE}Step 2: Running Inventory Scanner${NC}"
echo "Scanning both core and contrib repositories..."
echo ""

uv run python -m collector_watcher.scan_inventory \
    "$CONTRIB_REPO_PATH" \
    --core-repo="$CORE_REPO_PATH" \
    --mode=nightly

echo ""
echo -e "${GREEN}✓ Inventory scan complete${NC}"
echo ""

echo -e "${BLUE}Step 3: Verifying Inventory${NC}"
if [ -d "collector-metadata/core" ] && [ -d "collector-metadata/contrib" ]; then
    CORE_VERSIONS=$(ls -1 collector-metadata/core | wc -l)
    CONTRIB_VERSIONS=$(ls -1 collector-metadata/contrib | wc -l)
    echo -e "${GREEN}✓ Inventory directories found${NC}"
    echo "  Core versions: $CORE_VERSIONS"
    echo "  Contrib versions: $CONTRIB_VERSIONS"

    # Show latest version
    LATEST_CONTRIB=$(ls -1 collector-metadata/contrib | sort -V | tail -1)
    echo "  Latest contrib version: $LATEST_CONTRIB"

    # Count components in latest version
    if [ -f "collector-metadata/contrib/$LATEST_CONTRIB/receiver.yaml" ]; then
        RECEIVER_COUNT=$(grep -c "^  - name:" "collector-metadata/contrib/$LATEST_CONTRIB/receiver.yaml" || echo "0")
        echo "  Receivers in latest: $RECEIVER_COUNT"
    fi
else
    echo -e "${RED}✗ Inventory directories not found${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}Step 4: Checking Documentation Repository${NC}"
echo "Docs repo: $DOCS_REPO_PATH"
echo ""

if [ ! -d "$DOCS_REPO_PATH" ]; then
    echo -e "${YELLOW}Documentation repo not found at: $DOCS_REPO_PATH${NC}"
    echo "This should be your fork of opentelemetry.io"
    echo ""
    echo "Skipping documentation generation."
    echo "To include this step:"
    echo "  1. Clone your fork as a sibling directory: ../opentelemetry.io"
    echo "  2. Or set DOCS_REPO_PATH to your fork location"
    echo ""
    echo -e "${GREEN}===========================================${NC}"
    echo -e "${GREEN}Validation Complete (without docs update)${NC}"
    echo -e "${GREEN}===========================================${NC}"
    exit 0
fi

if [ -d "$DOCS_REPO_PATH/.git" ]; then
    echo -e "${GREEN}✓ Found docs repository (using your fork)${NC}"
else
    echo -e "${RED}✗ Directory exists but is not a git repository${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}Step 5: Generating Documentation${NC}"
echo "Updating documentation tables in your fork..."
echo ""

uv run python -m docs_automation.update_docs --docs-repo="$DOCS_REPO_PATH"

echo ""
echo -e "${GREEN}✓ Documentation updated${NC}"
echo ""

echo -e "${BLUE}Step 6: Formatting Documentation${NC}"
echo "Running npm run fix:format..."
cd "$DOCS_REPO_PATH"
npm run fix:format
cd - > /dev/null
echo ""
echo -e "${GREEN}✓ Documentation formatted${NC}"
echo ""

echo -e "${BLUE}Step 7: Documentation Changes${NC}"
cd "$DOCS_REPO_PATH"
if git diff --quiet content/en/docs/collector/components/; then
    echo -e "${YELLOW}No changes detected in documentation${NC}"
else
    echo -e "${GREEN}Documentation has been updated!${NC}"
    echo ""
    echo "Changed files:"
    git --no-pager diff --name-only content/en/docs/collector/components/
    echo ""
    echo "To review changes:"
    echo "  cd $DOCS_REPO_PATH"
    echo "  git diff content/en/docs/collector/components/"
    echo ""
    echo "To preview:"
    echo "  cd $DOCS_REPO_PATH"
    echo "  hugo server"
    echo "  # Open http://localhost:1313/docs/collector/components/"
fi
cd - > /dev/null

echo ""
echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}Validation Complete!${NC}"
echo -e "${GREEN}===========================================${NC}"
echo ""
echo "Summary:"
echo "  ✓ Repositories updated"
echo "  ✓ Inventory scanned and saved"
echo "  ✓ Documentation generated"
echo "  ✓ Documentation formatted"
echo ""
