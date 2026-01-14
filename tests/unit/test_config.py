import tempfile
from pathlib import Path

import pytest

from mdlint.config import (
    Configuration,
    apply_cli_overrides,
    build_rule_configs,
    find_config_file,
    load_config,
    parse_inline_config,
    parse_toml_file,
)
from tests.conftest import fixture_path


class TestFindConfigFile:
    """Tests for find_config_file function."""

    def test_find_mdlint_toml(self) -> None:
        """Find .mdlint.toml in fixtures."""
        # Use a subdirectory of the config fixture so it finds the fixture's config
        # and not the project's pyproject.toml
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_file = root / ".mdlint.toml"
            config_file.write_text("ignore = ['MD001']\n")

            result = find_config_file(root)

            assert result is not None
            assert result.name == ".mdlint.toml"

    def test_find_config_traverses_upward(self) -> None:
        """Find config file when starting from subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            subdir = root / "nested" / "deep"
            subdir.mkdir(parents=True)

            # Create config in root
            config_file = root / ".mdlint.toml"
            config_file.write_text("ignore = ['MD001']\n")

            result = find_config_file(subdir)

            assert result is not None
            assert result == config_file

    def test_returns_none_when_no_config_exists(self) -> None:
        """Return None when no config file exists in hierarchy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = find_config_file(Path(tmpdir))

            assert result is None

    def test_finds_pyproject_with_mdlint_section(self) -> None:
        """Find pyproject.toml only if it has [tool.mdlint] section."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create pyproject.toml with mdlint section
            pyproject = root / "pyproject.toml"
            pyproject.write_text("[tool.mdlint]\nignore = ['MD001']\n")

            result = find_config_file(root)

            assert result is not None
            assert result.name == "pyproject.toml"

    def test_ignores_pyproject_without_mdlint_section(self) -> None:
        """Ignore pyproject.toml if it lacks [tool.mdlint] section."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create pyproject.toml without mdlint section
            pyproject = root / "pyproject.toml"
            pyproject.write_text("[tool.other]\nkey = 'value'\n")

            result = find_config_file(root)

            assert result is None

    def test_prefers_mdlint_toml_over_pyproject(self) -> None:
        """Prefer .mdlint.toml over pyproject.toml in same directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create both config files
            (root / ".mdlint.toml").write_text("select = ['MD001']\n")
            (root / "pyproject.toml").write_text("[tool.mdlint]\nignore = ['MD001']\n")

            result = find_config_file(root)

            assert result is not None
            assert result.name == ".mdlint.toml"


class TestParseTomlFile:
    """Tests for parse_toml_file function."""

    def test_parse_mdlint_toml(self) -> None:
        """Parse .mdlint.toml file."""
        path = fixture_path("config", ".mdlint.toml")
        result = parse_toml_file(path)

        assert "ignore" in result
        assert result["ignore"] == ["MD041"]
        assert result["rules"]["MD003"]["style"] == "atx"

    def test_parse_pyproject_toml(self) -> None:
        """Parse pyproject.toml file."""
        path = fixture_path("config", "pyproject.toml")
        result = parse_toml_file(path)

        assert "select" in result
        assert result["select"] == ["MD001", "MD003", "MD004"]


class TestParseInlineConfig:
    """Tests for parse_inline_config function."""

    def test_parse_simple_rule_param(self) -> None:
        """Parse simple rule.param=value format."""
        result = parse_inline_config("MD003.style='atx'")

        assert result["rules"]["MD003"]["style"] == "atx"

    def test_parse_select_list(self) -> None:
        """Parse select list format (full TOML)."""
        result = parse_inline_config("select = ['MD001', 'MD002']")

        assert result["select"] == ["MD001", "MD002"]

    def test_parse_full_toml_section(self) -> None:
        """Parse full TOML section format."""
        result = parse_inline_config("[rules.MD003]\nstyle = 'atx'")

        assert result["rules"]["MD003"]["style"] == "atx"

    def test_invalid_toml_raises_error(self) -> None:
        """Invalid TOML raises TOMLDecodeError."""
        import sys

        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib  # type: ignore[import-not-found]

        with pytest.raises(tomllib.TOMLDecodeError):
            parse_inline_config("invalid = [unclosed")


class TestBuildRuleConfigs:
    """Tests for build_rule_configs function."""

    def test_build_from_dict(self) -> None:
        """Build rule configs from dictionary."""
        data = {
            "rules": {
                "MD003": {"style": "atx"},
            }
        }
        result = build_rule_configs(data)

        assert "MD003" in result
        assert result["MD003"].style == "atx"  # type: ignore[attr-defined]

    def test_build_with_empty_data(self) -> None:
        """Build rule configs with empty config data."""
        result = build_rule_configs({})

        # Should create default configs for all registered rules
        from mdlint.rules import RULE_REGISTRY

        for rule_id in RULE_REGISTRY:
            assert rule_id in result

    def test_build_with_no_rules_section(self) -> None:
        """Build rule configs when rules section is missing."""
        data = {"other": "data"}
        result = build_rule_configs(data)

        # Should create default configs for all registered rules
        from mdlint.rules import RULE_REGISTRY

        assert len(result) == len(RULE_REGISTRY)


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_from_file(self) -> None:
        """Load config from explicit file path."""
        path = fixture_path("config", ".mdlint.toml")
        result = load_config(config_path=str(path))

        assert result.source == str(path)
        assert "MD003" in result.rules
        assert result.ignore == ["MD041"]

    def test_load_with_inline_config(self) -> None:
        """Load config from inline TOML string."""
        result = load_config(config_path="MD003.style='atx'")

        assert result.source == "<inline>"
        assert result.rules["MD003"].style == "atx"  # type: ignore[attr-defined]

    def test_load_exclude_from_file(self) -> None:
        """Load exclude list from config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / ".mdlint.toml"
            config_file.write_text('exclude = ["docs/rules/", "*.tmp.md"]\n')

            result = load_config(config_path=str(config_file))

            assert result.exclude == ["docs/rules/", "*.tmp.md"]

    def test_load_defaults_exclude_to_empty(self) -> None:
        """Config without exclude defaults to empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / ".mdlint.toml"
            config_file.write_text('ignore = ["MD001"]\n')

            result = load_config(config_path=str(config_file))

            assert result.exclude == []


class TestApplyCliOverrides:
    """Tests for apply_cli_overrides function."""

    def test_select_replaces_baseline(self) -> None:
        """--select replaces the entire select baseline."""
        config = Configuration(select=["MD001", "MD002"])
        result = apply_cli_overrides(config, select=("MD003",))

        assert result.select == ["MD003"]

    def test_ignore_replaces_list(self) -> None:
        """--ignore replaces the entire ignore list."""
        config = Configuration(ignore=["MD001"])
        result = apply_cli_overrides(config, ignore=("MD002", "MD003"))

        assert result.ignore == ["MD002", "MD003"]

    def test_extend_select_adds_to_baseline(self) -> None:
        """--extend-select adds to the existing select list."""
        config = Configuration(select=["MD001"])
        result = apply_cli_overrides(config, extend_select=("MD002", "MD003"))

        assert result.select == ["MD001", "MD002", "MD003"]

    def test_extend_ignore_adds_to_list(self) -> None:
        """--extend-ignore adds to the existing ignore list."""
        config = Configuration(ignore=["MD001"])
        result = apply_cli_overrides(config, extend_ignore=("MD002",))

        assert result.ignore == ["MD001", "MD002"]

    def test_combined_overrides(self) -> None:
        """Combine multiple override options."""
        config = Configuration(select=["MD001"], ignore=["MD005"])
        result = apply_cli_overrides(
            config,
            extend_select=("MD002",),
            extend_ignore=("MD003",),
        )

        assert result.select == ["MD001", "MD002"]
        assert result.ignore == ["MD005", "MD003"]


class TestEnabledRules:
    """Tests for Configuration.enabled_rules property."""

    def test_no_config_enables_all(self) -> None:
        """Empty config enables all registered rules."""
        from mdlint.rules import RULE_REGISTRY

        config = Configuration()

        assert config.enabled_rules == set(RULE_REGISTRY.keys())

    def test_select_narrows_baseline(self) -> None:
        """select establishes a narrow baseline."""
        config = Configuration(select=["MD001", "MD003"])

        assert config.enabled_rules == {"MD001", "MD003"}

    def test_ignore_subtracts_from_all(self) -> None:
        """ignore subtracts from all rules when no select."""
        from mdlint.rules import RULE_REGISTRY

        config = Configuration(ignore=["MD001", "MD003"])

        expected = set(RULE_REGISTRY.keys()) - {"MD001", "MD003"}
        assert config.enabled_rules == expected

    def test_select_then_ignore(self) -> None:
        """ignore subtracts from select baseline."""
        config = Configuration(select=["MD001", "MD003", "MD004"], ignore=["MD003"])

        assert config.enabled_rules == {"MD001", "MD004"}

    def test_ignore_outside_select_is_noop(self) -> None:
        """Ignoring a rule not in select does nothing."""
        config = Configuration(select=["MD001", "MD003"], ignore=["MD010"])

        assert config.enabled_rules == {"MD001", "MD003"}
