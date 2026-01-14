import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]

from mdlint.rules import RULE_REGISTRY
from mdlint.rules.base import RuleConfig


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
    """
    rules_data = config_data.get("rules", {})
    return {
        rule_id: rule_class.config_class(**rules_data.get(rule_id, {}))
        for rule_id, rule_class in RULE_REGISTRY.items()
    }


def load_config(config_path: str | None = None) -> Configuration:
    """Load configuration from file or defaults.

    Args:
        config_path: Explicit config path or inline TOML.

    Returns:
        Merged Configuration object.
    """
    config_data: dict = {}
    source: str | None = None

    if config_path:
        path = Path(config_path)
        if path.is_file():
            config_data = parse_toml_file(path)
            source = str(path)
        else:
            # Treat as inline TOML
            config_data = parse_inline_config(config_path)
            source = "<inline>"
    else:
        # Search for config file
        found_path = find_config_file()
        if found_path:
            config_data = parse_toml_file(found_path)
            source = str(found_path)

    rule_configs = build_rule_configs(config_data)

    # Extract select/ignore/exclude lists
    select = config_data.get("select", [])
    ignore = config_data.get("ignore", [])
    exclude = config_data.get("exclude", [])

    return Configuration(
        rules=rule_configs,
        select=select,
        ignore=ignore,
        exclude=exclude,
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
