"""Template merge and validation helpers."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .errors import DuplicateKeyError, TemplateSyncError


class UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate mapping keys."""


def _construct_mapping(
    loader: UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise DuplicateKeyError(f"Duplicate YAML key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


@dataclass(frozen=True)
class MergeResult:
    """Merged templates and source metadata."""

    templates: dict[str, Any]
    source_files: list[str]
    digest: str
    inheritance_edges: dict[str, list[str]]


def resolve_config_path(path: str | Path, config_root: str | Path) -> Path:
    """Resolve a path and require it to remain inside the config root."""
    root = Path(config_root).expanduser().resolve()
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as err:
        raise TemplateSyncError(
            f"Path must be inside config root: {candidate}"
        ) from err
    return candidate


def merge_template_folder(
    template_folder: str | Path, config_root: str | Path
) -> MergeResult:
    """Read and merge YAML template files from a folder deterministically."""
    folder = resolve_config_path(template_folder, config_root)
    if not folder.exists():
        raise TemplateSyncError(f"Template folder does not exist: {folder}")
    if not folder.is_dir():
        raise TemplateSyncError(f"Template folder is not a directory: {folder}")

    files = sorted(
        (path for path in folder.iterdir() if path.suffix.lower() in {".yaml", ".yml"}),
        key=lambda path: path.name.lower(),
    )
    if not files:
        raise TemplateSyncError(f"No .yaml or .yml files found in: {folder}")

    merged: dict[str, Any] = {}
    source_files: list[str] = []
    digest_hash = hashlib.sha256()

    for path in files:
        source_files.append(str(path))
        raw = path.read_text(encoding="utf-8-sig")
        digest_hash.update(path.name.encode("utf-8"))
        digest_hash.update(b"\0")
        digest_hash.update(raw.encode("utf-8"))
        data = yaml.load(raw, Loader=UniqueKeyLoader)
        if data is None:
            continue
        if not isinstance(data, dict):
            raise TemplateSyncError(f"YAML file root must be a mapping: {path}")
        for template_name, template_config in data.items():
            if not isinstance(template_name, str):
                raise TemplateSyncError(
                    f"Template names must be strings in {path}: {template_name!r}"
                )
            if template_name in merged:
                raise TemplateSyncError(
                    f"Duplicate template name across files: {template_name!r}"
                )
            merged[template_name] = template_config

    if not merged:
        raise TemplateSyncError(f"Merged template mapping is empty: {folder}")

    inheritance_edges = validate_template_inheritance(merged)
    return MergeResult(
        templates=merged,
        source_files=source_files,
        digest=digest_hash.hexdigest(),
        inheritance_edges=inheritance_edges,
    )


def _template_refs(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    raise TemplateSyncError("template must be a string or list of strings")


def validate_template_inheritance(templates: dict[str, Any]) -> dict[str, list[str]]:
    """Validate button-card template references and reject cycles."""
    edges: dict[str, list[str]] = {}
    for name, config in templates.items():
        refs: list[str] = []
        if isinstance(config, dict) and "template" in config:
            refs = _template_refs(config["template"])
        elif config is not None and not isinstance(config, dict):
            raise TemplateSyncError(f"Template {name!r} must be a mapping or null")

        for ref in refs:
            if ref not in templates:
                raise TemplateSyncError(
                    f"Template {name!r} references missing template {ref!r}"
                )
        edges[name] = refs

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str, stack: list[str]) -> None:
        if name in visited:
            return
        if name in visiting:
            cycle = " -> ".join([*stack, name])
            raise TemplateSyncError(f"Template inheritance cycle detected: {cycle}")
        visiting.add(name)
        for ref in edges[name]:
            visit(ref, [*stack, name])
        visiting.remove(name)
        visited.add(name)

    for name in templates:
        visit(name, [])

    return edges
