"""AsyncAPI 3.0 extractor for `common/asyncapi/*.yaml`.

Emits one row per operation, using method `WS` and path `{channel}:{operation}`.
These rows default to auth level ``Unspecified``; the cross-linking logic in
``collect_endpoints.py`` fills in the real auth level from the implementer
(e.g. sbm) when available.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))
from models import Auth, EndpointRow  # noqa: E402
from extractors import _yaml_scan  # noqa: E402


def extract(common_root: Path) -> tuple[list[EndpointRow], list[str]]:
    aa_dir = common_root / "asyncapi"
    if not aa_dir.exists():
        return [], []
    rows: list[EndpointRow] = []
    warnings: list[str] = []
    for yaml_file in sorted(aa_dir.glob("*.yaml")) + sorted(aa_dir.glob("*.yml")):
        try:
            keys = _yaml_scan.read(yaml_file)
        except OSError as exc:
            warnings.append(f"cannot read {yaml_file.name}: {exc!r}")
            continue
        top = {k.key for k in keys if k.indent == 0}
        if "asyncapi" not in top:
            continue
        repo_name = _repo_name_from_yaml(yaml_file)

        channels_idx = _yaml_scan.find_top_level(keys, "channels")
        operations_idx = _yaml_scan.find_top_level(keys, "operations")

        # Map channel-key → address (the `address:` field). We accept both:
        #   channels:
        #     BacktestChannel:
        #       address: /sbm/v1/ws
        channel_addresses: dict[str, str] = {}
        if channels_idx is not None:
            for ch_i in _yaml_scan.children_of(keys, channels_idx):
                ch_name = keys[ch_i].key
                address = ""
                for sub_i in _yaml_scan.children_of(keys, ch_i):
                    if keys[sub_i].key == "address":
                        address = keys[sub_i].inline_value.strip("'\"") or ""
                        break
                channel_addresses[ch_name] = address

        if operations_idx is None:
            # AsyncAPI 2.x style: channels contain the operations directly.
            for ch_name, address in channel_addresses.items():
                rows.append(
                    EndpointRow(
                        repository=repo_name,
                        method="WS",
                        path=address or f"channel:{ch_name}",
                        auth=Auth.UNSPECIFIED,
                        source_kind="AsyncAPI spec",
                    )
                )
            continue

        for op_i in _yaml_scan.children_of(keys, operations_idx):
            op_name = keys[op_i].key
            channel_ref = ""
            for sub_i in _yaml_scan.children_of(keys, op_i):
                sk = keys[sub_i]
                if sk.key == "channel":
                    # channel is usually `$ref: '#/channels/BacktestChannel'`
                    for r_i in _yaml_scan.children_of(keys, sub_i):
                        if keys[r_i].key == "$ref":
                            ref = keys[r_i].inline_value.strip("'\"")
                            m = re.match(r"#/channels/(.+)", ref)
                            if m:
                                channel_ref = m.group(1)
                    if not channel_ref and sk.inline_value:
                        # In-line ref
                        m = re.match(r"#/channels/(.+)", sk.inline_value.strip("'\""))
                        if m:
                            channel_ref = m.group(1)
            address = channel_addresses.get(channel_ref, "")
            path = f"{address}:{op_name}" if address else f"channel:{channel_ref}:{op_name}"
            rows.append(
                EndpointRow(
                    repository=repo_name,
                    method="WS",
                    path=path,
                    auth=Auth.UNSPECIFIED,
                    source_kind="AsyncAPI spec",
                )
            )
    return rows, warnings


def _repo_name_from_yaml(file: Path) -> str:
    stem = file.stem
    stem = re.sub(r"-v\d+$", "", stem)
    return stem
