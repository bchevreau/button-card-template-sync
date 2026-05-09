"""Tests for template folder merge and validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from button_card_template_sync.errors import (
    DuplicateKeyError,
    TemplateSyncError,
)
from button_card_template_sync.merge import (
    merge_template_folder,
    resolve_config_path,
    validate_template_inheritance,
)


def write_yaml(folder: Path, name: str, content: str) -> None:
    """Write a YAML fixture file."""
    (folder / name).write_text(content, encoding="utf-8")


def test_merge_template_folder_sorts_files_and_accepts_utf8_bom(
    tmp_path: Path,
) -> None:
    """Merge direct YAML children in deterministic filename order."""
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    write_yaml(template_dir, "b.yaml", "second:\n  template: first\n")
    (template_dir / "a.yaml").write_text(
        "\ufefffirst:\n  show_icon: true\n",
        encoding="utf-8",
    )

    result = merge_template_folder(template_dir, tmp_path)

    assert list(result.templates) == ["first", "second"]
    assert result.inheritance_edges == {"first": [], "second": ["first"]}
    assert [Path(path).name for path in result.source_files] == ["a.yaml", "b.yaml"]


def test_merge_template_folder_rejects_duplicate_yaml_keys(tmp_path: Path) -> None:
    """Reject duplicate mapping keys inside one YAML file."""
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    write_yaml(template_dir, "templates.yaml", "base: {}\nbase: {}\n")

    with pytest.raises(DuplicateKeyError, match="Duplicate YAML key"):
        merge_template_folder(template_dir, tmp_path)


def test_merge_template_folder_rejects_duplicate_template_names(
    tmp_path: Path,
) -> None:
    """Reject duplicate template names across files."""
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    write_yaml(template_dir, "a.yaml", "base: {}\n")
    write_yaml(template_dir, "b.yaml", "base: {}\n")

    with pytest.raises(TemplateSyncError, match="Duplicate template name"):
        merge_template_folder(template_dir, tmp_path)


def test_merge_template_folder_rejects_non_mapping_root(tmp_path: Path) -> None:
    """Reject YAML files whose root is not a mapping."""
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    write_yaml(template_dir, "templates.yaml", "- base\n")

    with pytest.raises(TemplateSyncError, match="root must be a mapping"):
        merge_template_folder(template_dir, tmp_path)


def test_merge_template_folder_rejects_missing_template_reference(
    tmp_path: Path,
) -> None:
    """Reject inheritance references to missing templates."""
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    write_yaml(template_dir, "templates.yaml", "child:\n  template: missing\n")

    with pytest.raises(TemplateSyncError, match="references missing template"):
        merge_template_folder(template_dir, tmp_path)


def test_validate_template_inheritance_rejects_cycles() -> None:
    """Reject recursive template inheritance cycles."""
    templates = {
        "a": {"template": "b"},
        "b": {"template": ["c"]},
        "c": {"template": "a"},
    }

    with pytest.raises(TemplateSyncError, match="cycle detected"):
        validate_template_inheritance(templates)


def test_validate_template_inheritance_rejects_invalid_template_field() -> None:
    """Reject non-string and non-list template references."""
    with pytest.raises(TemplateSyncError, match="template must be"):
        validate_template_inheritance({"bad": {"template": {"not": "valid"}}})


def test_resolve_config_path_rejects_path_escape(tmp_path: Path) -> None:
    """Reject paths that resolve outside the Home Assistant config root."""
    outside = tmp_path.parent

    with pytest.raises(TemplateSyncError, match="inside config root"):
        resolve_config_path(outside, tmp_path)
