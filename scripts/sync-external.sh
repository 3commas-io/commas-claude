#!/bin/bash
#
# Sync external agents, commands, and skills from wshobson/agents
# Usage: ./scripts/sync-external.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
REPO_URL="https://github.com/wshobson/agents.git"
AGENTS_EXTERNAL_DIR="$REPO_DIR/agents/external"
COMMANDS_EXTERNAL_DIR="$REPO_DIR/commands/external"
SKILLS_EXTERNAL_DIR="$REPO_DIR/skills/external"
CONFIG_FILE="$REPO_DIR/config/external-agents.txt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Syncing external agents, commands, and skills from wshobson/agents..."
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

# Ensure external directories exist
mkdir -p "$AGENTS_EXTERNAL_DIR"
mkdir -p "$COMMANDS_EXTERNAL_DIR"
mkdir -p "$SKILLS_EXTERNAL_DIR"

# Clear existing external content (to remove deleted ones)
rm -f "$AGENTS_EXTERNAL_DIR"/*.md
rm -f "$COMMANDS_EXTERNAL_DIR"/*.md
rm -rf "$SKILLS_EXTERNAL_DIR"/*/

# Counters
AGENT_COUNT=0
COMMAND_COUNT=0
SKILL_COUNT=0
PLUGIN_COUNT=0

# Read plugin list and copy agents, commands, and skills
while IFS= read -r plugin || [ -n "$plugin" ]; do
    # Skip comments and empty lines
    [[ "$plugin" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${plugin// }" ]] && continue

    plugin=$(echo "$plugin" | xargs)  # Trim whitespace
    PLUGIN_BASE="$TEMP_DIR/plugins/$plugin"

    if [ ! -d "$PLUGIN_BASE" ]; then
        echo -e "  ${YELLOW}⚠${NC} Plugin not found: $plugin"
        continue
    fi

    found=0

    # === AGENTS ===
    AGENTS_DIR="$PLUGIN_BASE/agents"
    if [ -d "$AGENTS_DIR" ]; then
        for agent_file in "$AGENTS_DIR"/*.md; do
            if [ -f "$agent_file" ]; then
                cp "$agent_file" "$AGENTS_EXTERNAL_DIR/"
                echo -e "  ${GREEN}→${NC} agent: $(basename "$agent_file")"
                ((AGENT_COUNT++))
                found=1
            fi
        done
    fi

    # === COMMANDS ===
    CMD_DIR="$PLUGIN_BASE/commands"
    if [ -d "$CMD_DIR" ]; then
        for cmd_file in "$CMD_DIR"/*.md; do
            if [ -f "$cmd_file" ]; then
                cp "$cmd_file" "$COMMANDS_EXTERNAL_DIR/"
                echo -e "  ${GREEN}→${NC} command: $(basename "$cmd_file")"
                ((COMMAND_COUNT++))
                found=1
            fi
        done
    fi

    # === SKILLS ===
    SKILL_SRC="$PLUGIN_BASE/skills"
    if [ -d "$SKILL_SRC" ]; then
        for skill_dir in "$SKILL_SRC"/*/; do
            if [ -d "$skill_dir" ]; then
                skill_name=$(basename "$skill_dir")
                if [ -f "$skill_dir/SKILL.md" ]; then
                    mkdir -p "$SKILLS_EXTERNAL_DIR/$skill_name"
                    cp "$skill_dir/SKILL.md" "$SKILLS_EXTERNAL_DIR/$skill_name/"
                    echo -e "  ${GREEN}→${NC} skill: $skill_name"
                    ((SKILL_COUNT++))
                    found=1
                fi
            fi
        done
    fi

    if [ $found -eq 1 ]; then
        ((PLUGIN_COUNT++))
    fi
done < "$CONFIG_FILE"

# Create/update attribution files

# Agents README
cat > "$AGENTS_EXTERNAL_DIR/README.md" << EOF
# External Agents

Vendored from [wshobson/agents](https://github.com/wshobson/agents) (MIT License).

| Attribute | Value |
|-----------|-------|
| **Last synced** | $(date -u +"%Y-%m-%d %H:%M UTC") |
| **Source commit** | [$COMMIT_HASH](https://github.com/wshobson/agents/commit/$COMMIT_HASH) |
| **Agents** | $AGENT_COUNT |
| **Plugins** | $PLUGIN_COUNT |

## Updating

\`\`\`bash
make sync-external
\`\`\`

To add/remove plugins, edit \`config/external-agents.txt\` and re-run sync.

## Included Plugins

$(grep -v '^#' "$CONFIG_FILE" | grep -v '^$' | sed 's/^/- /')
EOF

# Commands README
cat > "$COMMANDS_EXTERNAL_DIR/README.md" << EOF
# External Commands

Vendored from [wshobson/agents](https://github.com/wshobson/agents) (MIT License).

These are slash commands (e.g., \`/python-scaffold\`) from external plugins.

| Attribute | Value |
|-----------|-------|
| **Last synced** | $(date -u +"%Y-%m-%d %H:%M UTC") |
| **Source commit** | [$COMMIT_HASH](https://github.com/wshobson/agents/commit/$COMMIT_HASH) |
| **Commands** | $COMMAND_COUNT |

## Updating

\`\`\`bash
make sync-external
\`\`\`
EOF

# Skills README
cat > "$SKILLS_EXTERNAL_DIR/README.md" << EOF
# External Skills

Vendored from [wshobson/agents](https://github.com/wshobson/agents) (MIT License).

Skills are modular knowledge packages that provide context and best practices.

| Attribute | Value |
|-----------|-------|
| **Last synced** | $(date -u +"%Y-%m-%d %H:%M UTC") |
| **Source commit** | [$COMMIT_HASH](https://github.com/wshobson/agents/commit/$COMMIT_HASH) |
| **Skills** | $SKILL_COUNT |

## Updating

\`\`\`bash
make sync-external
\`\`\`
EOF

# Write sync timestamp
echo "$(date -u +%Y-%m-%d)" > "$AGENTS_EXTERNAL_DIR/.last-sync"

echo ""
echo -e "${GREEN}✓${NC} Synced from $PLUGIN_COUNT plugins:"
echo -e "  - $AGENT_COUNT agents"
echo -e "  - $COMMAND_COUNT commands"
echo -e "  - $SKILL_COUNT skills"
