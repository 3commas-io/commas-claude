r"""Indent-aware YAML scanner tailored to OpenAPI 3.x and AsyncAPI 3.0.

Not a general YAML parser. It returns structural information that's
sufficient for enumerating HTTP paths / operations / channels / security
schemes. Avoids a pyyaml dependency so the skill works on a vanilla
Python install.

Design: walk lines, track (indent, key). Keys are lines matching
``^(\s*)([^:\s][^:]*):\s*(.*)$`` with comments/blanks skipped. Each
emitted event is ``(indent, key, inline_value, line_no)``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


_KEY_RE = re.compile(r"^(\s*)([^\s#].*?)\s*:\s*(.*?)\s*$")
_LIST_RE = re.compile(r"^(\s*)-\s*(.*?)\s*$")


@dataclass
class YamlKey:
    indent: int
    key: str
    inline_value: str
    line: int  # 1-based


def scan_keys(text: str) -> list[YamlKey]:
    out: list[YamlKey] = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        # Strip comments
        line = _strip_comment(raw)
        if not line.strip():
            continue
        # Skip list items (we don't need their scalar content at this level).
        m_list = _LIST_RE.match(line)
        if m_list and ":" not in m_list.group(2):
            continue
        m = _KEY_RE.match(line)
        if not m:
            continue
        indent = len(m.group(1))
        key = _unquote(m.group(2).strip())
        inline_value = m.group(3).strip()
        out.append(YamlKey(indent=indent, key=key, inline_value=inline_value, line=lineno))
    return out


def _strip_comment(line: str) -> str:
    # Simple: anything from `# ` onwards that isn't inside quotes.
    in_str: str | None = None
    escape = False
    for i, ch in enumerate(line):
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_str:
                in_str = None
            continue
        if ch in ("'", '"'):
            in_str = ch
            continue
        if ch == "#":
            # Only treat as comment if preceded by whitespace or at start.
            if i == 0 or line[i - 1].isspace():
                return line[:i]
    return line


def _unquote(s: str) -> str:
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s


def children_of(keys: list[YamlKey], parent_idx: int) -> list[int]:
    """Return indices of direct children of `keys[parent_idx]`."""
    parent_indent = keys[parent_idx].indent
    out: list[int] = []
    child_indent = None
    for i in range(parent_idx + 1, len(keys)):
        k = keys[i]
        if k.indent <= parent_indent:
            break
        if child_indent is None:
            child_indent = k.indent
            out.append(i)
        elif k.indent == child_indent:
            out.append(i)
    return out


def find_top_level(keys: list[YamlKey], name: str) -> int | None:
    # Top-level keys have indent 0.
    for i, k in enumerate(keys):
        if k.indent == 0 and k.key == name:
            return i
    return None


def read(path: Path) -> list[YamlKey]:
    return scan_keys(path.read_text())
