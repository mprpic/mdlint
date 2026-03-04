import dataclasses
import importlib
import re
import sys
import zipfile
from dataclasses import fields
from pathlib import Path
from typing import Literal, get_args, get_origin

from mdlint.rules import RULE_REGISTRY

_RULE_PAGE_RE = re.compile(r"^rules/(md\d+)\.md$")


def on_config(config):  # noqa: ARG001
    """Reload rule modules so that live-reload picks up source changes."""
    # Reload individual rule modules first, then the package itself
    # so RULE_REGISTRY is rebuilt from fresh module state.
    global RULE_REGISTRY
    for name in sorted(k for k in sys.modules if k.startswith("mdlint.rules.md")):
        importlib.reload(sys.modules[name])
    importlib.reload(sys.modules["mdlint.rules"])
    from mdlint.rules import RULE_REGISTRY  # noqa: PLC0415


def _build_rule_doc(rule_id: str) -> str:
    """Build the full Markdown documentation for a rule."""
    rule_class = RULE_REGISTRY[rule_id]

    # Extract configuration fields
    config_class = rule_class.config_class
    config_fields = []
    for f in fields(config_class):
        # Extract available options from Literal types
        options = "-"
        type_hint = f.type
        # Handle string annotations by evaluating them
        if isinstance(type_hint, str):
            type_hint = eval(type_hint, dict(vars(config_class)))  # noqa: S307
        if get_origin(type_hint) is Literal:
            args = get_args(type_hint)
            if args:
                options = ", ".join(args)

        # Resolve default value (default_factory for list fields)
        if f.default is not dataclasses.MISSING:
            default = f.default
        elif f.default_factory is not dataclasses.MISSING:
            default = f.default_factory()
        else:
            default = None

        metadata = f.metadata if f.metadata else {}
        description = metadata.get("description", "")
        option_descriptions = metadata.get("option_descriptions", {})

        config_fields.append(
            {
                "name": f.name,
                "default": default,
                "options": options,
                "description": description,
                "option_descriptions": option_descriptions,
            }
        )

    parts = [
        # Front matter
        "---\nhide:\n  - toc\n---\n",
        # Title
        f"# {rule_class.id} - {rule_class.name}\n",
        "## Description\n",
        f"{rule_class.description or ''}\n",
        "## Rationale\n",
        f"{rule_class.rationale or ''}\n",
    ]
    if config_fields:
        parts.append("## Configuration\n")
        for field in config_fields:
            field_lines = [f"**`{field['name']}`**", f":   {field['description']}", ""]
            default = field["default"]
            if isinstance(default, list):
                if default:
                    formatted = ", ".join(f'"{item}"' for item in default)
                    field_lines.append(f"    - **Default:** `[{formatted}]`")
                else:
                    field_lines.append("    - **Default:** `[]` (empty)")
            else:
                if default == "":
                    default_str = '"" (empty string)'
                else:
                    default_str = str(default).lower()
                field_lines.append(f"    - **Default:** `{default_str}`")
            if field["option_descriptions"]:
                field_lines.append("    - **Options:**")
                for opt, desc in field["option_descriptions"].items():
                    field_lines.append(f"        - `{opt}`: {desc}")
            elif field["options"] != "-":
                field_lines.append(f"    - **Options:** `{field['options']}`")
            parts.append("\n".join(field_lines) + "\n")

    example_valid = (rule_class.example_valid or "").strip()
    example_invalid = (rule_class.example_invalid or "").strip()
    if example_valid or example_invalid:
        parts.append("## Examples\n")
        if example_invalid:
            parts.append("### Invalid\n")
            parts.append(f"````markdown\n{example_invalid}\n````\n")
        if example_valid:
            parts.append("### Valid\n")
            parts.append(f"````markdown\n{example_valid}\n````\n")

    return "\n".join(parts)


def _build_rules_index_table() -> str:
    """Build the rules table for the rules index page."""
    lines = [
        "| Rule | Name | Summary |",
        "|------|------|---------|",
    ]
    for rule_id in sorted(RULE_REGISTRY.keys()):
        rule_class = RULE_REGISTRY[rule_id]
        lines.append(
            f"| [{rule_class.id}](./{rule_class.id.lower()}.md) "
            f"| {rule_class.name} "
            f"| {rule_class.summary} |"
        )
    return "\n".join(lines)


def on_page_read_source(page, config) -> str | None:  # noqa: ARG001
    """Generate source content for rule pages (runs before front matter parsing)."""
    match = _RULE_PAGE_RE.match(page.file.src_path)
    if match:
        rule_id = match.group(1).upper()
        if rule_id in RULE_REGISTRY:
            return _build_rule_doc(rule_id)
    return None


def on_page_markdown(markdown: str, page, config, files) -> str:  # noqa: ARG001
    """Generate the rules table for the rules index page."""
    if page.file.src_path == "rules/index.md":
        return markdown + "\n\n" + _build_rules_index_table()
    return markdown


def on_post_build(config) -> None:
    """Build mdlint source archive for the browser playground."""
    site_dir = Path(config["site_dir"])
    assets_dir = site_dir / "assets"
    assets_dir.mkdir(exist_ok=True)

    src_dir = Path("src/mdlint")
    zip_path = assets_dir / "mdlint-src.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for py_file in sorted(src_dir.rglob("*.py")):
            arcname = str(py_file.relative_to("src"))
            zf.write(py_file, arcname)
