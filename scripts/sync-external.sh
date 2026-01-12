#!/bin/bash
#
# Sync external agents, commands, and skills from wshobson/agents
# Usage: ./scripts/sync-external.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
REPO_URL="https://github.com/wshobson/agents.git"
AGENTS_DIR="$REPO_DIR/agents"
COMMANDS_DIR="$REPO_DIR/commands"
SKILLS_DIR="$REPO_DIR/skills"
CONFIG_FILE="$REPO_DIR/config/external-agents.txt"

# Custom files to preserve (not deleted during sync)
CUSTOM_AGENTS=("github-pr.md" "jira-status-report.md")
CUSTOM_SKILLS=("3commas-guidelines")

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
SYNC_DATE=$(date -u +"%Y-%m-%d %H:%M UTC")
echo "Source commit: $COMMIT_HASH"
echo ""

# Ensure directories exist
mkdir -p "$AGENTS_DIR"
mkdir -p "$COMMANDS_DIR"
mkdir -p "$SKILLS_DIR"

# Clear existing external content (preserve custom files)
echo "Clearing old vendored content..."
for file in "$AGENTS_DIR"/*.md; do
    [ -f "$file" ] || continue
    filename=$(basename "$file")
    # Skip custom agents
    skip=0
    for custom in "${CUSTOM_AGENTS[@]}"; do
        if [ "$filename" = "$custom" ]; then
            skip=1
            break
        fi
    done
    if [ $skip -eq 0 ]; then
        rm -f "$file"
    fi
done

# Clear commands (all are external)
rm -f "$COMMANDS_DIR"/*.md

# Clear skills (preserve custom)
for dir in "$SKILLS_DIR"/*/; do
    [ -d "$dir" ] || continue
    dirname=$(basename "$dir")
    skip=0
    for custom in "${CUSTOM_SKILLS[@]}"; do
        if [ "$dirname" = "$custom" ]; then
            skip=1
            break
        fi
    done
    if [ $skip -eq 0 ]; then
        rm -rf "$dir"
    fi
done

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
        echo -e "  ${YELLOW}Warning:${NC} Plugin not found: $plugin"
        continue
    fi

    found=0

    # === AGENTS ===
    SRC_AGENTS="$PLUGIN_BASE/agents"
    if [ -d "$SRC_AGENTS" ]; then
        for agent_file in "$SRC_AGENTS"/*.md; do
            if [ -f "$agent_file" ]; then
                cp "$agent_file" "$AGENTS_DIR/"
                echo -e "  ${GREEN}+${NC} agent: $(basename "$agent_file")"
                ((AGENT_COUNT++))
                found=1
            fi
        done
    fi

    # === COMMANDS ===
    SRC_COMMANDS="$PLUGIN_BASE/commands"
    if [ -d "$SRC_COMMANDS" ]; then
        for cmd_file in "$SRC_COMMANDS"/*.md; do
            if [ -f "$cmd_file" ]; then
                cp "$cmd_file" "$COMMANDS_DIR/"
                echo -e "  ${GREEN}+${NC} command: $(basename "$cmd_file")"
                ((COMMAND_COUNT++))
                found=1
            fi
        done
    fi

    # === SKILLS ===
    SRC_SKILLS="$PLUGIN_BASE/skills"
    if [ -d "$SRC_SKILLS" ]; then
        for skill_dir in "$SRC_SKILLS"/*/; do
            if [ -d "$skill_dir" ]; then
                skill_name=$(basename "$skill_dir")
                if [ -f "$skill_dir/SKILL.md" ]; then
                    mkdir -p "$SKILLS_DIR/$skill_name"
                    cp "$skill_dir/SKILL.md" "$SKILLS_DIR/$skill_name/"
                    echo -e "  ${GREEN}+${NC} skill: $skill_name"
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

# Get plugin list for README
PLUGIN_LIST=$(grep -v '^#' "$CONFIG_FILE" | grep -v '^$' | sed 's/^/- /')

# Create attribution README in agents/
cat > "$AGENTS_DIR/README.md" << EOF
# Agents

This directory contains Claude Code agents from two sources:

## Custom 3Commas Agents
- \`github-pr.md\` - GitHub PR creation agent
- \`jira-status-report.md\` - Jira status reporting agent

## Vendored External Agents ($AGENT_COUNT)

Synced from [wshobson/agents](https://github.com/wshobson/agents) (MIT License).

| Attribute | Value |
|-----------|-------|
| **Last synced** | $SYNC_DATE |
| **Source commit** | [$COMMIT_HASH](https://github.com/wshobson/agents/commit/$COMMIT_HASH) |

### Updating

\`\`\`bash
make sync-external
\`\`\`

To add/remove plugins, edit \`config/external-agents.txt\` and re-run sync.
EOF

# Create README in commands/
cat > "$COMMANDS_DIR/README.md" << EOF
# Commands

Slash commands (e.g., \`/tdd-red\`) vendored from [wshobson/agents](https://github.com/wshobson/agents) (MIT License).

| Attribute | Value |
|-----------|-------|
| **Last synced** | $SYNC_DATE |
| **Source commit** | [$COMMIT_HASH](https://github.com/wshobson/agents/commit/$COMMIT_HASH) |
| **Commands** | $COMMAND_COUNT |

## Updating

\`\`\`bash
make sync-external
\`\`\`
EOF

# Create README in skills/
cat > "$SKILLS_DIR/README.md" << EOF
# Skills

Knowledge modules that provide context and best practices.

## Custom 3Commas Skills
- \`3commas-guidelines/\` - Organization coding standards

## Vendored External Skills ($SKILL_COUNT)

Synced from [wshobson/agents](https://github.com/wshobson/agents) (MIT License).

| Attribute | Value |
|-----------|-------|
| **Last synced** | $SYNC_DATE |
| **Source commit** | [$COMMIT_HASH](https://github.com/wshobson/agents/commit/$COMMIT_HASH) |

## Updating

\`\`\`bash
make sync-external
\`\`\`
EOF

# Write sync timestamp
echo "$SYNC_DATE" > "$REPO_DIR/.last-sync"

echo ""
echo -e "${GREEN}Synced from $PLUGIN_COUNT plugins:${NC}"
echo -e "  - $AGENT_COUNT agents (+ 2 custom)"
echo -e "  - $COMMAND_COUNT commands"
echo -e "  - $SKILL_COUNT skills (+ 1 custom)"
