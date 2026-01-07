#!/usr/bin/env python3
"""
Generate AGENTS.md documentation from agent files.
Usage: python3 scripts/generate-docs.py
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# Try to use PyYAML, fall back to basic parsing if not available
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# Category definitions: (emoji, name, patterns)
CATEGORIES = [
    ("🏢", "3Commas", ["github-pr", "jira-status-report"]),
    ("🎸", "Django", ["django-*", "django"]),
    ("💎", "Rails", ["rails-*"]),
    ("🟠", "Laravel", ["laravel-*"]),
    ("🐍", "Python", ["python-*", "fastapi-*"]),
    ("⚛️", "Frontend", ["vue-*", "react-*", "frontend-*"]),
    ("🔍", "Code Quality", ["code-reviewer", "code-archaeologist"]),
    ("⚡", "Performance", ["performance-*"]),
    ("🎯", "Orchestration", ["*-orchestrator", "*-configurator", "project-analyst"]),
    ("📊", "Data & ML", ["ml-*", "web-scraping-*"]),
    ("🛡️", "DevOps & Quality", ["security-*", "testing-*", "devops-*"]),
    ("🔧", "Backend & API", ["backend-*", "api-*"]),
    ("📝", "Other", ["documentation-*", "tailwind-*"]),
]


def match_pattern(name: str, pattern: str) -> bool:
    """Match agent name against a glob-like pattern."""
    if pattern.startswith("*"):
        return name.endswith(pattern[1:])
    elif pattern.endswith("*"):
        return name.startswith(pattern[:-1])
    else:
        return name == pattern


def get_category(agent_name: str) -> Tuple[str, str]:
    """Determine category for an agent based on name patterns."""
    for emoji, category, patterns in CATEGORIES:
        for pattern in patterns:
            if match_pattern(agent_name, pattern):
                return emoji, category
    return "📦", "Uncategorized"


def parse_front_matter_basic(content: str) -> Dict:
    """Parse YAML front matter without PyYAML (basic fallback)."""
    result = {}
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return result

    yaml_content = match.group(1)
    for line in yaml_content.split('\n'):
        line = line.strip()
        if ':' in line and not line.startswith('#'):
            key, _, value = line.partition(':')
            key = key.strip()
            value = value.strip().strip('"\'')
            result[key] = value
    return result


def parse_front_matter(content: str) -> Dict:
    """Parse YAML front matter from markdown content."""
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return {}

    yaml_content = match.group(1)

    if HAS_YAML:
        try:
            return yaml.safe_load(yaml_content) or {}
        except yaml.YAMLError:
            return parse_front_matter_basic(content)
    else:
        return parse_front_matter_basic(content)


def extract_triggers(content: str) -> Optional[str]:
    """Extract trigger phrases from agent content."""
    # Look for trigger section
    match = re.search(r'##\s*Trigger\s*\n+(.*?)(?=\n##|\Z)', content, re.DOTALL | re.IGNORECASE)
    if match:
        trigger_text = match.group(1).strip()
        # Extract quoted phrases
        phrases = re.findall(r'"([^"]+)"', trigger_text)
        if phrases:
            return ", ".join(f'"{p}"' for p in phrases[:4])
    return None


def parse_agent_file(filepath: Path, is_external: bool = False) -> Optional[Dict]:
    """Parse a single agent file and extract metadata."""
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Warning: Could not read {filepath}: {e}")
        return None

    meta = parse_front_matter(content)
    if not meta:
        return None

    # Get agent name from front matter or filename
    name = meta.get('name', filepath.stem)

    # Clean up name (remove file extension if present)
    if isinstance(name, str):
        name = name.replace('.md', '')

    # Get category
    emoji, category = get_category(filepath.stem)

    # Extract triggers if available
    triggers = extract_triggers(content)

    return {
        'filename': filepath.stem,
        'name': name,
        'description': meta.get('description', 'No description'),
        'model': meta.get('model', '-'),
        'tools': meta.get('tools', ''),
        'category': category,
        'emoji': emoji,
        'triggers': triggers,
        'version': meta.get('version', ''),
        'tags': meta.get('tags', []),
        'is_external': is_external,
    }


def generate_docs(agents_dir: Path, output_file: Path):
    """Generate AGENTS.md from all agent files."""

    # Parse all agents (custom)
    agents = []
    for filepath in sorted(agents_dir.glob('*.md')):
        agent = parse_agent_file(filepath, is_external=False)
        if agent:
            agents.append(agent)

    # Parse external agents
    external_dir = agents_dir / 'external'
    external_count = 0
    if external_dir.exists():
        for filepath in sorted(external_dir.glob('*.md')):
            if filepath.name == 'README.md':
                continue
            agent = parse_agent_file(filepath, is_external=True)
            if agent:
                agents.append(agent)
                external_count += 1

    if not agents:
        print("No agents found!")
        return

    custom_count = len(agents) - external_count

    # Group by category
    by_category = defaultdict(list)
    for agent in agents:
        by_category[(agent['emoji'], agent['category'])].append(agent)

    # Sort categories by the order defined in CATEGORIES
    category_order = {cat: i for i, (_, cat, _) in enumerate(CATEGORIES)}
    category_order['Uncategorized'] = 999
    sorted_categories = sorted(by_category.keys(), key=lambda x: category_order.get(x[1], 998))

    # Generate markdown
    lines = []

    # Header
    lines.append("# 🤖 3Commas Claude Agents")
    lines.append("")
    lines.append("> **Auto-generated documentation.** Run `make docs` to update.")
    lines.append("")

    # Overview
    lines.append("## 📊 Overview")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Agents | {len(agents)} |")
    lines.append(f"| Custom (3Commas) | {custom_count} |")
    if external_count > 0:
        lines.append(f"| External ([wshobson/agents](https://github.com/wshobson/agents)) | {external_count} |")
    lines.append(f"| Categories | {len(by_category)} |")
    lines.append("")

    # Table of Contents
    lines.append("## 📑 Categories")
    lines.append("")
    for emoji, category in sorted_categories:
        count = len(by_category[(emoji, category)])
        anchor = category.lower().replace(' ', '-').replace('&', '')
        lines.append(f"- [{emoji} {category}](#{anchor}) ({count})")
    lines.append("")

    # Quick Reference Table
    lines.append("## 📋 Quick Reference")
    lines.append("")
    lines.append("| Agent | Description | Category | Source |")
    lines.append("|-------|-------------|----------|--------|")
    for agent in sorted(agents, key=lambda x: x['filename']):
        desc = agent['description'][:55] + "..." if len(agent['description']) > 55 else agent['description']
        source = "external" if agent['is_external'] else "custom"
        lines.append(f"| `{agent['filename']}` | {desc} | {agent['emoji']} {agent['category']} | {source} |")
    lines.append("")

    # Category sections
    for emoji, category in sorted_categories:
        category_agents = by_category[(emoji, category)]
        anchor = category.lower().replace(' ', '-').replace('&', '')

        lines.append(f"## {emoji} {category}")
        lines.append("")

        for agent in sorted(category_agents, key=lambda x: x['filename']):
            external_badge = " ↗" if agent['is_external'] else ""
            lines.append(f"### {agent['filename']}{external_badge}")
            lines.append("")
            lines.append(f"> {agent['description']}")
            lines.append("")

            # Metadata table
            meta_items = []
            if agent['model'] and agent['model'] != '-':
                meta_items.append(f"**Model:** `{agent['model']}`")
            if agent['triggers']:
                meta_items.append(f"**Triggers:** {agent['triggers']}")
            if agent['version']:
                meta_items.append(f"**Version:** {agent['version']}")
            if agent['is_external']:
                meta_items.append("**Source:** [wshobson/agents](https://github.com/wshobson/agents)")

            if meta_items:
                lines.append(" | ".join(meta_items))
                lines.append("")

            lines.append("---")
            lines.append("")

    # Write output
    output_file.write_text('\n'.join(lines), encoding='utf-8')
    ext_msg = f", {external_count} external" if external_count > 0 else ""
    print(f"✓ Generated {output_file} ({len(agents)} agents: {custom_count} custom{ext_msg})")


def main():
    # Determine paths relative to script location
    script_dir = Path(__file__).parent
    repo_dir = script_dir.parent
    agents_dir = repo_dir / 'agents'
    output_file = repo_dir / 'AGENTS.md'

    if not agents_dir.exists():
        print(f"Error: Agents directory not found: {agents_dir}")
        return 1

    generate_docs(agents_dir, output_file)
    return 0


if __name__ == '__main__':
    exit(main())
