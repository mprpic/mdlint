import dataclasses
import json
import re
import sys
import types
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]

from mdlint.rules import RULE_REGISTRY, resolve_rule_id
from mdlint.rules.base import RuleConfig

_TYPE_NAMES: dict[Any, str] = {bool: "boolean", int: "integer", str: "string"}

# Every key a config file may hold at its top level (under [tool.mdlint] in pyproject.toml)
_TOP_LEVEL_KEYS = ("exclude", "ignore", "rules", "select")


class ConfigError(Exception):
    """Invalid configuration.

    Raised instead of letting bad values reach rule code, where they would either crash
    with a traceback or silently change what a rule checks.
    """


def _toml_value(value: Any) -> str:
    """Render a parsed value close to how it was written in TOML, for error messages."""
    return json.dumps(value, ensure_ascii=False, default=str)


def _describe(hint: Any) -> str:
    """Describe a type hint in the words used for config error messages."""
    origin = get_origin(hint)
    args = get_args(hint)
    if origin is Literal:
        return "one of " + ", ".join(_toml_value(arg) for arg in args)
    if origin in (Union, types.UnionType):
        return " or ".join(_describe(arg) for arg in args if arg is not type(None))
    if origin is list:
        return f"a list of {_TYPE_NAMES.get(args[0], args[0].__name__)}s"
    name = _TYPE_NAMES.get(hint, getattr(hint, "__name__", str(hint)))
    return f"an {name}" if name[0] in "aeiou" else f"a {name}"


def _matches(value: Any, hint: Any) -> bool:
    """Check a parsed TOML value against a config field's type hint."""
    origin = get_origin(hint)
    args = get_args(hint)
    if origin is Literal:
        return any(type(value) is type(arg) and value == arg for arg in args)
    if origin in (Union, types.UnionType):
        return any(_matches(value, arg) for arg in args)
    if origin is list:
        return isinstance(value, list) and all(_matches(item, args[0]) for item in value)
    if hint is int:
        # TOML booleans are Python bools, which are also ints
        return isinstance(value, int) and not isinstance(value, bool)
    expected = origin or hint
    if isinstance(expected, type):
        return isinstance(value, expected)
    return True


def _type_error(key: str, value: Any, hint: Any) -> ConfigError:
    """Build the error for a value of the wrong type.

    A comma-separated string for a list option is a likely mistake, so the message shows
    the list it was probably meant to be.
    """
    message = f"{key}: Expected {_describe(hint)}, got {_toml_value(value)}"
    accepts_list = any(get_origin(arg) is list for arg in (hint, *get_args(hint)))
    if accepts_list and isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
        message += f"; write it as {key.rsplit('.', 1)[-1]} = {_toml_value(items)}"
    return ConfigError(message)


def _build_rule_config(rule_id: str, key: str, options: Any) -> RuleConfig:
    """Validate one `[rules.<key>]` table against the rule's config dataclass."""
    if not isinstance(options, dict):
        raise ConfigError(f"{key}: Expected a table of options, got {_toml_value(options)}")
    config_class = RULE_REGISTRY[rule_id].config_class
    hints = get_type_hints(config_class)
    fields = {f.name: f for f in dataclasses.fields(config_class)}
    field_names = fields.keys()
    for name, value in options.items():
        if name not in field_names:
            message = f"{key}.{name}: Unknown option"
            if name.replace("-", "_") in field_names:
                message += f" (did you mean {name.replace('-', '_')}?)"
            raise ConfigError(message)
        if not _matches(value, hints[name]):
            raise _type_error(f"{key}.{name}", value, hints[name])
        if fields[name].metadata.get("regex"):
            try:
                re.compile(value)
            except re.error as e:
                raise ConfigError(f"{key}.{name}: Invalid regular expression: {e}") from None
    return config_class(**options)


def resolve_rule_names(names: Iterable[str]) -> list[str]:
    """Map rule names written by a user to rule IDs.

    Raises:
        ConfigError: If any name matches no rule; every unknown name is listed so the user
            can fix them all at once.
    """
    resolved: list[str] = []
    unknown: list[str] = []
    for name in names:
        rule_id = resolve_rule_id(name)
        if rule_id is None:
            unknown.append(name)
        else:
            resolved.append(rule_id)
    if unknown:
        raise ConfigError(f"Unknown rule(s): {', '.join(unknown)}")
    return resolved


@dataclass
class Configuration:
    """Represents the merged configuration from all sources.

    Attributes:
        rules: Rule ID -> config mapping.
        select: Rules to enable (baseline). Empty means all rules.
        ignore: Rules to disable (subtracted from select).
        source: Path to config file used, or None for defaults.
    """

    rules: dict[str, RuleConfig] = field(default_factory=dict)
    select: list[str] = field(default_factory=list)
    ignore: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    source: str | None = None

    @property
    def enabled_rules(self) -> set[str]:
        """Compute the set of enabled rule IDs.

        select establishes the baseline (all rules if empty),
        then ignore subtracts from it.
        """
        # Baseline: select list or all registered rules
        if self.select:
            baseline = set(self.select)
        else:
            baseline = set(RULE_REGISTRY.keys())

        # Subtract ignored rules
        return baseline - set(self.ignore)


def find_config_file(start_dir: Path | None = None) -> Path | None:
    """Search upward for configuration file.

    Searches for .mdlint.toml first, then pyproject.toml.

    Args:
        start_dir: Directory to start searching from. Defaults to cwd.

    Returns:
        Path to config file, or None if not found.
    """
    current = (start_dir or Path.cwd()).resolve()
    while current != current.parent:
        # Check for .mdlint.toml first
        mdlint_config = current / ".mdlint.toml"
        if mdlint_config.is_file():
            return mdlint_config

        # Check for pyproject.toml with [tool.mdlint] section
        pyproject = current / "pyproject.toml"
        if pyproject.is_file():
            try:
                with pyproject.open("rb") as f:
                    data = tomllib.load(f)
                if "tool" in data and "mdlint" in data["tool"]:
                    return pyproject
            except (tomllib.TOMLDecodeError, OSError):
                pass

        current = current.parent

    return None


def parse_toml_file(path: Path) -> dict:
    """Parse TOML file and extract mdlint configuration.

    Args:
        path: Path to TOML file.

    Returns:
        Configuration dictionary.
    """
    with path.open("rb") as f:
        data = tomllib.load(f)

    # Handle pyproject.toml format
    if path.name == "pyproject.toml":
        return data.get("tool", {}).get("mdlint", {})

    return data


def parse_inline_config(config_str: str) -> dict:
    """Parse inline TOML configuration string.

    Args:
        config_str: Inline TOML string (e.g., "MD003.style='atx'").

    Returns:
        Configuration dictionary.
    """
    # Top-level config keys that should not be wrapped in [rules]
    top_level_keys = {"select", "ignore", "exclude"}

    # Handle simple key=value format
    if "=" in config_str and not config_str.strip().startswith("["):
        # Convert MD003.style='atx' to [rules.MD003]\nstyle = 'atx'
        key_path, value = config_str.split("=", 1)
        key_path = key_path.strip()
        value = value.strip()

        if key_path in top_level_keys:
            # Keep as top-level config
            config_str = f"{key_path} = {value}"
        elif "." in key_path:
            rule_id, param = key_path.rsplit(".", 1)
            config_str = f"[rules.{rule_id}]\n{param} = {value}"
        else:
            config_str = f"[rules]\n{key_path} = {value}"

    return tomllib.loads(config_str)


def build_rule_configs(config_data: dict) -> dict[str, RuleConfig]:
    """Build rule configurations from parsed config data.

    Args:
        config_data: Parsed configuration dictionary.

    Returns:
        Mapping of rule ID to RuleConfig.

    Raises:
        ConfigError: If a rule section names no rule, configures a rule twice, or holds an
            unknown option or a value of the wrong type.
    """
    rules_data = config_data.get("rules", {})
    if not isinstance(rules_data, dict):
        raise ConfigError(f"rules: Expected a table, got {_toml_value(rules_data)}")

    rule_configs = {
        rule_id: rule_class.config_class() for rule_id, rule_class in RULE_REGISTRY.items()
    }
    # Sections may use a rule name or any case, so track the key each rule ID came from
    configured_keys: dict[str, str] = {}
    for key, options in rules_data.items():
        rule_id = resolve_rule_id(key)
        if rule_id is None:
            raise ConfigError(f"rules.{key}: Unknown rule")
        if rule_id in configured_keys:
            raise ConfigError(f"rules.{key}: Duplicates rules.{configured_keys[rule_id]}")
        configured_keys[rule_id] = key
        rule_configs[rule_id] = _build_rule_config(rule_id, f"rules.{key}", options)
    return rule_configs


def _string_list(config_data: dict, key: str) -> list[str]:
    """Validate a top-level list option such as `exclude`."""
    value = config_data.get(key, [])
    if not _matches(value, list[str]):
        raise _type_error(key, value, list[str])
    return value


def _rule_list(config_data: dict, key: str) -> list[str]:
    """Validate `select`/`ignore` the same way as the CLI flags, mapping names to rule IDs."""
    names = _string_list(config_data, key)
    try:
        return resolve_rule_names(names)
    except ConfigError as e:
        raise ConfigError(f"{key}: {e}") from None


def load_config(config_path: str | None = None) -> Configuration:
    """Load configuration from file or defaults.

    Args:
        config_path: Explicit config path or inline TOML.

    Returns:
        Merged Configuration object.

    Raises:
        ConfigError: If the config file is missing, is not valid TOML, or holds invalid
            settings. The message names the config source.
    """
    config_data: dict = {}
    source: str | None = None

    if config_path:
        if Path(config_path).is_file():
            source = str(Path(config_path))
        elif "=" in config_path:
            # Treat as inline TOML
            source = "<inline>"
        else:
            raise ConfigError(f"Config file not found: {config_path}")
    else:
        # Search for config file
        found_path = find_config_file()
        if found_path:
            source = str(found_path)

    try:
        if source == "<inline>":
            config_data = parse_inline_config(config_path or "")
        elif source:
            config_data = parse_toml_file(Path(source))

        return build_configuration(config_data, source)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{source}: Invalid TOML: {e}") from None
    except ConfigError as e:
        raise ConfigError(f"{source}: {e}") from None


def build_configuration(config_data: dict, source: str | None = None) -> Configuration:
    """Validate parsed settings and turn them into a Configuration.

    load_config() uses this for config files and inline TOML, and the docs playground calls
    it with the TOML typed into the page, so both accept and reject the same settings.

    Args:
        config_data: Parsed settings, in the shape of a .mdlint.toml file.
        source: Where the settings came from, recorded on the Configuration.

    Raises:
        ConfigError: If a key, rule name or option value is invalid.
    """
    for key in config_data:
        if key not in _TOP_LEVEL_KEYS:
            valid = ", ".join(_TOP_LEVEL_KEYS)
            raise ConfigError(f"{key}: Unknown option (valid options: {valid})")

    return Configuration(
        rules=build_rule_configs(config_data),
        select=_rule_list(config_data, "select"),
        ignore=_rule_list(config_data, "ignore"),
        exclude=_string_list(config_data, "exclude"),
        source=source,
    )


def apply_cli_overrides(
    config: Configuration,
    select: tuple[str, ...] | None = None,
    ignore: tuple[str, ...] | None = None,
    extend_select: tuple[str, ...] | None = None,
    extend_ignore: tuple[str, ...] | None = None,
) -> Configuration:
    """Apply CLI rule selection overrides.

    Args:
        config: Base configuration.
        select: Replaces the entire select baseline.
        ignore: Replaces the entire ignore list.
        extend_select: Adds to the existing select list.
        extend_ignore: Adds to the existing ignore list.

    Returns:
        Modified Configuration.
    """
    if select:
        config.select = list(select)

    if ignore:
        config.ignore = list(ignore)

    if extend_select:
        config.select.extend(extend_select)

    if extend_ignore:
        config.ignore.extend(extend_ignore)

    return config
