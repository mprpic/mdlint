import re
import tempfile
import tomllib
from pathlib import Path

import pytest

from mdlint.config import (
    ConfigError,
    Configuration,
    apply_cli_overrides,
    build_configuration,
    build_rule_configs,
    find_config_file,
    load_config,
    parse_inline_config,
    parse_toml_file,
    resolve_rule_names,
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

    def test_rule_section_by_name(self) -> None:
        """A rule section may be named by rule name instead of ID."""
        result = build_rule_configs({"rules": {"line-length": {"line_length": 100}}})

        assert result["MD013"].line_length == 100  # type: ignore[attr-defined]

    def test_rule_section_lowercase_id(self) -> None:
        """A rule section ID is matched case-insensitively."""
        result = build_rule_configs({"rules": {"md013": {"line_length": 5}}})

        assert result["MD013"].line_length == 5  # type: ignore[attr-defined]

    def test_optional_fields_accept_values(self) -> None:
        """Options typed `X | None` accept a value of type X."""
        result = build_rule_configs(
            {
                "rules": {
                    "MD007": {"start_indent": 4},
                    "MD033": {"table_allowed_elements": ["br"]},
                }
            }
        )

        assert result["MD007"].start_indent == 4  # type: ignore[attr-defined]
        assert result["MD033"].table_allowed_elements == ["br"]  # type: ignore[attr-defined]


class TestBuildRuleConfigsErrors:
    """Invalid rule configuration raises ConfigError naming the rule and key."""

    @pytest.mark.parametrize(
        ("rules", "message"),
        [
            ({"MD013": {"stern": True}}, "rules.MD013.stern: Unknown option"),
            (
                {"MD013": {"line-length": 100}},
                "rules.MD013.line-length: Unknown option (did you mean line_length?)",
            ),
            ({"MD013": False}, "rules.MD013: Expected a table of options, got false"),
            (
                {"MD022": {"lines_above": [1, 2, 1, 1, 1, 1]}},
                "rules.MD022.lines_above: Expected an integer, got [1, 2, 1, 1, 1, 1]",
            ),
            (
                {"MD013": {"line_length": True}},
                "rules.MD013.line_length: Expected an integer, got true",
            ),
            (
                {"MD013": {"code_blocks": "no"}},
                'rules.MD013.code_blocks: Expected a boolean, got "no"',
            ),
            (
                {"MD033": {"allowed_elements": ["br", 1]}},
                'rules.MD033.allowed_elements: Expected a list of strings, got ["br", 1]',
            ),
            (
                {"MD029": {"style": "one-or-ordered"}},
                'rules.MD029.style: Expected one of "one", "ordered", "one_or_ordered", '
                '"zero", got "one-or-ordered"',
            ),
            ({"MD060": {"style": "aligned-no-space"}}, "rules.MD060.style: Expected one of"),
            ({"MD007": {"start_indent": "4"}}, "rules.MD007.start_indent: Expected an integer"),
            ({"MD999": {}}, "rules.MD999: Unknown rule"),
            (
                {"MD013": {"line_length": 100}, "line-length": {"line_length": 120}},
                "rules.line-length: Duplicates rules.MD013",
            ),
        ],
    )
    def test_invalid_rule_config(self, rules: dict, message: str) -> None:
        with pytest.raises(ConfigError) as exc_info:
            build_rule_configs({"rules": rules})

        assert str(exc_info.value).startswith(message)

    def test_string_for_list_option_shows_list_form(self) -> None:
        """A comma-separated string for a list option is an error that shows the list form."""
        with pytest.raises(ConfigError) as exc_info:
            build_rule_configs({"rules": {"MD033": {"allowed_elements": "br, img"}}})

        assert str(exc_info.value) == (
            'rules.MD033.allowed_elements: Expected a list of strings, got "br, img"; '
            'write it as allowed_elements = ["br", "img"]'
        )

    def test_rules_not_a_table(self) -> None:
        with pytest.raises(ConfigError, match="^rules: Expected a table"):
            build_rule_configs({"rules": ["MD013"]})


class TestRegexOptions:
    """Options that hold a regular expression are compiled when the config is loaded."""

    @pytest.mark.parametrize(
        ("rule", "option"), [("MD041", "front_matter_title"), ("MD051", "ignored_pattern")]
    )
    def test_invalid_regex_is_a_config_error(self, rule: str, option: str) -> None:
        with pytest.raises(
            ConfigError, match=f"^rules.{rule}.{option}: Invalid regular expression: "
        ):
            build_rule_configs({"rules": {rule: {option: "("}}})

    def test_valid_regex_is_accepted(self) -> None:
        configs = build_rule_configs({"rules": {"MD041": {"front_matter_title": "^name:"}}})

        assert configs["MD041"].front_matter_title == "^name:"


class TestResolveRuleNames:
    """Tests for resolve_rule_names function."""

    def test_resolves_ids_and_names(self) -> None:
        assert resolve_rule_names(["md013", "line-length", "MD001"]) == ["MD013", "MD013", "MD001"]

    def test_unknown_names_raise(self) -> None:
        with pytest.raises(ConfigError, match="^Unknown rule\\(s\\): MD999, nope$"):
            resolve_rule_names(["MD001", "MD999", "nope"])


class TestBuildConfiguration:
    """build_configuration validates parsed settings the way config files are validated."""

    def test_resolves_rule_names(self) -> None:
        config = build_configuration({"ignore": ["first-line-heading"]})

        assert config.ignore == ["MD041"]
        assert "MD041" not in config.enabled_rules

    @pytest.mark.parametrize(
        ("data", "message"),
        [
            ({"ignore": "MD041"}, "^ignore: "),
            ({"selct": ["MD001"]}, "^selct: Unknown option"),
            ({"rules": {"MD004": {"styel": "dash"}}}, "^rules.MD004.styel: Unknown option"),
        ],
    )
    def test_rejects_invalid_settings(self, data: dict, message: str) -> None:
        with pytest.raises(ConfigError, match=message):
            build_configuration(data)


class TestLoadConfigErrors:
    """load_config reports problems as ConfigError prefixed with the config source."""

    def test_invalid_toml_file(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".mdlint.toml"
        config_file.write_text("[rules.MD013\n")

        with pytest.raises(ConfigError, match=f"^{re.escape(str(config_file))}: Invalid TOML: "):
            load_config(config_path=str(config_file))

    def test_invalid_toml_discovered_file(self, tmp_path: Path, monkeypatch) -> None:
        (tmp_path / ".mdlint.toml").write_text("[rules.MD013\n")
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ConfigError, match="Invalid TOML"):
            load_config()

    def test_invalid_inline_toml(self) -> None:
        with pytest.raises(ConfigError, match="^<inline>: Invalid TOML: "):
            load_config(config_path="MD013.line_length=[")

    def test_missing_config_file(self, tmp_path: Path) -> None:
        missing = tmp_path / "missing.toml"

        with pytest.raises(
            ConfigError, match=f"^Config file not found: {re.escape(str(missing))}$"
        ):
            load_config(config_path=str(missing))

    def test_rule_error_names_source(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".mdlint.toml"
        config_file.write_text("[rules.MD013]\nstern = true\n")

        with pytest.raises(
            ConfigError, match=f"^{re.escape(str(config_file))}: rules.MD013.stern: Unknown option"
        ):
            load_config(config_path=str(config_file))

    def test_inline_rule_error_names_source(self) -> None:
        with pytest.raises(ConfigError, match="^<inline>: rules.MD029.style: Expected one of"):
            load_config(config_path="MD029.style='one-or-ordered'")

    def test_unknown_top_level_key(self, tmp_path: Path) -> None:
        """A misspelled setting must not be ignored, or the config silently does nothing."""
        config_file = tmp_path / ".mdlint.toml"
        config_file.write_text('selct = ["MD001"]\n')

        with pytest.raises(ConfigError) as exc_info:
            load_config(config_path=str(config_file))

        assert str(exc_info.value) == (
            f"{config_file}: selct: Unknown option (valid options: exclude, ignore, rules, select)"
        )

    def test_unknown_key_in_pyproject(self, tmp_path: Path) -> None:
        config_file = tmp_path / "pyproject.toml"
        config_file.write_text('[tool.mdlint]\nselct = ["MD001"]\n\n[tool.other]\nkey = 1\n')

        with pytest.raises(
            ConfigError, match=f"^{re.escape(str(config_file))}: selct: Unknown option"
        ):
            load_config(config_path=str(config_file))

    def test_unknown_key_in_inline_config(self) -> None:
        with pytest.raises(ConfigError, match="^<inline>: selct: Unknown option"):
            load_config(config_path="select = ['MD001']\nselct = ['MD002']")

    @pytest.mark.parametrize("key", ["select", "ignore"])
    def test_unknown_rule_in_rule_list(self, tmp_path: Path, key: str) -> None:
        config_file = tmp_path / ".mdlint.toml"
        config_file.write_text(f'{key} = ["MD001", "line-lenght"]\n')

        with pytest.raises(
            ConfigError,
            match=f"^{re.escape(str(config_file))}: {key}: Unknown rule\\(s\\): line-lenght$",
        ):
            load_config(config_path=str(config_file))

    @pytest.mark.parametrize("key", ["select", "ignore", "exclude"])
    def test_string_for_top_level_list(self, tmp_path: Path, key: str) -> None:
        config_file = tmp_path / ".mdlint.toml"
        config_file.write_text(f'{key} = "MD013"\n')

        with pytest.raises(ConfigError) as exc_info:
            load_config(config_path=str(config_file))

        assert str(exc_info.value) == (
            f'{config_file}: {key}: Expected a list of strings, got "MD013"; '
            f'write it as {key} = ["MD013"]'
        )


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

    def test_select_and_ignore_resolve_names(self, tmp_path: Path) -> None:
        """select/ignore accept rule names and lowercase IDs and store rule IDs."""
        config_file = tmp_path / ".mdlint.toml"
        config_file.write_text(
            'select = ["line-length", "md001"]\nignore = ["heading-increment"]\n'
        )

        result = load_config(config_path=str(config_file))

        assert result.select == ["MD013", "MD001"]
        assert result.ignore == ["MD001"]
        assert result.enabled_rules == {"MD013"}

    def test_inline_config_with_rule_name(self) -> None:
        result = load_config(config_path="line-length.line_length=100")

        assert result.rules["MD013"].line_length == 100  # type: ignore[attr-defined]


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
