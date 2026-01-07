#!/bin/bash
#
# Sync external agents from wshobson/agents
# Usage: ./scripts/sync-external.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
REPO_URL="https://github.com/wshobson/agents.git"
EXTERNAL_DIR="$REPO_DIR/agents/external"
CONFIG_FILE="$REPO_DIR/config/external-agents.txt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Syncing external agents from wshobson/agents..."
echo ""

# Check config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: Config file not found: $CONFIG_FILE${NC}"
    exit 1
fi

# Create temp directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Clone repo (shallow)
echo "Cloning wshobson/agents (shallow)..."
git clone --depth 1 --quiet "$REPO_URL" "$TEMP_DIR"

# Get commit hash for attribution
COMMIT_HASH=$(cd "$TEMP_DIR" && git rev-parse --short HEAD)
echo "Source commit: $COMMIT_HASH"
echo ""

# Ensure external directory exists
mkdir -p "$EXTERNAL_DIR"

# Clear existing external agents (to remove deleted ones)
rm -f "$EXTERNAL_DIR"/*.md

# Count agents
AGENT_COUNT=0
PLUGIN_COUNT=0

# Read plugin list and copy agents
while IFS= read -r plugin || [ -n "$plugin" ]; do
    # Skip comments and empty lines
    [[ "$plugin" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${plugin// }" ]] && continue

    plugin=$(echo "$plugin" | xargs)  # Trim whitespace

    PLUGIN_DIR="$TEMP_DIR/plugins/$plugin/agents"

    if [ -d "$PLUGIN_DIR" ]; then
        found=0
        for agent_file in "$PLUGIN_DIR"/*.md; do
            if [ -f "$agent_file" ]; then
                cp "$agent_file" "$EXTERNAL_DIR/"
                echo -e "  ${GREEN}→${NC} $(basename "$agent_file") (from $plugin)"
                ((AGENT_COUNT++))
                found=1
            fi
        done
        if [ $found -eq 1 ]; then
            ((PLUGIN_COUNT++))
        fi
    else
        echo -e "  ${YELLOW}⚠${NC} Plugin not found: $plugin"
    fi
done < "$CONFIG_FILE"

# Create/update attribution file
cat > "$EXTERNAL_DIR/README.md" << EOF
# External Agents

Vendored from [wshobson/agents](https://github.com/wshobson/agents) (MIT License).

| Attribute | Value |
|-----------|-------|
| **Last synced** | $(date -u +"%Y-%m-%d %H:%M UTC") |
| **Source commit** | [$COMMIT_HASH](https://github.com/wshobson/agents/commit/$COMMIT_HASH) |
| **Agents** | $AGENT_COUNT |
| **Plugins** | $PLUGIN_COUNT |

## Updating

To update these agents:

\`\`\`bash
make sync-external
\`\`\`

To add/remove plugins, edit \`config/external-agents.txt\` and re-run sync.

## Included Plugins

$(grep -v '^#' "$CONFIG_FILE" | grep -v '^$' | sed 's/^/- /')
EOF

# Write sync timestamp
echo "$(date -u +%Y-%m-%d)" > "$EXTERNAL_DIR/.last-sync"

echo ""
echo -e "${GREEN}✓${NC} Synced $AGENT_COUNT agents from $PLUGIN_COUNT plugins"
