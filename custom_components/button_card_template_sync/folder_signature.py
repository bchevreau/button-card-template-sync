"""Folder signature helpers for Button Card Template Sync."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .errors import TemplateSyncError
from .merge import resolve_config_path


@dataclass(frozen=True)
class FolderSignature:
    """Cheap signature for direct YAML files in a folder."""

    digest: str
    file_count: int
    files: list[str]


def compute_folder_signature(
    template_folder: str | Path, config_root: str | Path
) -> FolderSignature:
    """Compute a cheap direct-child YAML file signature."""
    folder = resolve_config_path(template_folder, config_root)
    if not folder.exists():
        raise TemplateSyncError(f"Template folder does not exist: {folder}")
    if not folder.is_dir():
        raise TemplateSyncError(f"Template folder is not a directory: {folder}")

    files = sorted(
        (path for path in folder.iterdir() if path.suffix.lower() in {".yaml", ".yml"}),
        key=lambda path: path.name.lower(),
    )
    digest_hash = hashlib.sha256()
    names: list[str] = []
    for path in files:
        stat = path.stat()
        names.append(path.name)
        digest_hash.update(path.name.encode("utf-8"))
        digest_hash.update(b"\0")
        digest_hash.update(str(stat.st_size).encode("utf-8"))
        digest_hash.update(b"\0")
        digest_hash.update(str(stat.st_mtime_ns).encode("utf-8"))
        digest_hash.update(b"\0")

    return FolderSignature(
        digest=digest_hash.hexdigest(),
        file_count=len(files),
        files=names,
    )
