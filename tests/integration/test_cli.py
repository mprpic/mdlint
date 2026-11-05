import io
import json
import sys

import pytest
from click.testing import CliRunner

from mdlint.cli import cli
from tests.conftest import fixture_path, load_fixture


class TestCLICheck:
    """Integration tests for mdlint check command."""

    @pytest.fixture(autouse=True)
    def _no_project_config(self, monkeypatch) -> None:
        """Prevent tests from picking up the project's .mdlint.toml."""
        monkeypatch.setattr("mdlint.config.find_config_file", lambda start_dir=None: None)

    def test_check_clean_file(self) -> None:
        """Check a file with no violations."""
        runner = CliRunner()
        path = fixture_path("cli", "clean.md")

        result = runner.invoke(cli, ["check", str(path)])

        assert result.exit_code == 0

    def test_check_file_with_violations(self) -> None:
        """Check a file with violations."""
        runner = CliRunner()
        path = fixture_path("cli", "with_violations.md")

        result = runner.invoke(cli, ["check", str(path)])

        assert result.exit_code == 1
        assert "MD001" in result.output or "MD004" in result.output

    def test_check_stdin(self) -> None:
        """Check content from stdin."""
        runner = CliRunner()
        content = "# Valid heading\n\nSome content.\n"

        result = runner.invoke(cli, ["check", "-"], input=content)

        assert result.exit_code == 0

    def test_check_stdin_with_violations(self) -> None:
        """Check stdin content with violations."""
        runner = CliRunner()
        content = "# H1\n\n### H3\n"  # Skips h2

        result = runner.invoke(cli, ["check", "-"], input=content)

        assert result.exit_code == 1
        assert "MD001" in result.output

    def test_check_json_output(self) -> None:
        """Check with JSON output format."""
        runner = CliRunner()
        path = fixture_path("cli", "with_violations.md")

        result = runner.invoke(cli, ["check", "--format", "json", str(path)])

        assert result.exit_code == 1
        output = json.loads(result.output)
        assert "files" in output
        assert "summary" in output
        assert output["summary"]["total_violations"] >= 1

    def test_check_json_clean_file(self) -> None:
        """Check clean file with JSON output."""
        runner = CliRunner()
        path = fixture_path("cli", "clean.md")

        result = runner.invoke(cli, ["check", "--format", "json", str(path)])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["summary"]["total_violations"] == 0

    def test_check_multiple_files(self) -> None:
        """Check multiple files."""
        runner = CliRunner()
        clean_path = fixture_path("cli", "clean.md")
        violations_path = fixture_path("cli", "with_violations.md")

        result = runner.invoke(cli, ["check", str(clean_path), str(violations_path)])

        assert result.exit_code == 1

    def test_check_nonexistent_file(self) -> None:
        """Check nonexistent file."""
        runner = CliRunner()

        result = runner.invoke(cli, ["check", "nonexistent.md"])

        assert result.exit_code == 2

    def test_check_directory(self) -> None:
        """Check a directory with multiple files."""
        runner = CliRunner()
        path = fixture_path("multifile", "")

        result = runner.invoke(cli, ["check", str(path)])

        # Should find violations in with_violations.md
        assert result.exit_code == 1
        assert "MD001" in result.output

    def test_check_directory_with_json(self) -> None:
        """Check directory with JSON output."""
        runner = CliRunner()
        path = fixture_path("multifile", "")

        result = runner.invoke(cli, ["check", "--format", "json", str(path)])

        assert result.exit_code == 1
        output = json.loads(result.output)
        assert output["summary"]["files_checked"] >= 3

    def test_check_verbose_flag(self) -> None:
        """Test --verbose flag."""
        runner = CliRunner()
        path = fixture_path("multifile", "")

        result = runner.invoke(cli, ["check", "-v", str(path)])

        # Verbose output goes to stderr, captured in result.output with mix_stderr=True
        assert result.exit_code == 1

    def test_check_no_ignore_flag(self) -> None:
        """Test --no-ignore flag."""
        runner = CliRunner()
        path = fixture_path("multifile", "")

        result = runner.invoke(cli, ["check", "--no-ignore", str(path)])

        assert result.exit_code == 1

    def test_check_select_single_rule(self) -> None:
        """Select only a single rule to run."""
        runner = CliRunner()
        path = fixture_path("cli", "with_violations.md")

        result = runner.invoke(cli, ["check", "--select", "MD001", str(path)])

        assert result.exit_code == 1
        assert "MD001" in result.output

    def test_check_unknown_rule(self) -> None:
        """Error when selecting unknown rule."""
        runner = CliRunner()
        path = fixture_path("cli", "clean.md")

        result = runner.invoke(cli, ["check", "--select", "MD999", str(path)])

        assert result.exit_code == 2
        assert "Unknown rule" in result.output
        assert "MD999" in result.output

    def test_check_show_files(self) -> None:
        """Test --show-files flag lists files without linting."""
        runner = CliRunner()
        path = fixture_path("multifile", "")

        result = runner.invoke(cli, ["check", "--show-files", str(path)])

        assert result.exit_code == 0
        assert ".md" in result.output
        # Should not contain violation output
        assert "MD001" not in result.output

    def test_check_select_multiple_rules(self) -> None:
        """Select multiple rules with repeated --select options."""
        runner = CliRunner()
        # Content that triggers MD001 (h1->h3) and MD041 (first heading not h1)
        content = "## H2 First\n\n#### H4\n"

        result = runner.invoke(
            cli, ["check", "--select", "MD001", "--select", "MD041", "-"], input=content
        )

        assert result.exit_code == 1
        assert "MD001" in result.output
        assert "MD041" in result.output
        # Should not have other rules
        assert "MD003" not in result.output
        assert "MD004" not in result.output

    def test_check_ignore_single_rule(self) -> None:
        """Ignore a single rule with --ignore."""
        runner = CliRunner()
        # Content that triggers MD001 (h1->h3)
        content = "# H1\n\n### H3\n"

        result = runner.invoke(cli, ["check", "--ignore", "MD001", "-"], input=content)

        assert result.exit_code == 0
        assert "MD001" not in result.output

    def test_check_ignore_multiple_rules(self) -> None:
        """Ignore multiple rules with repeated --ignore options."""
        runner = CliRunner()
        # Content that triggers MD001 and MD041
        content = "## H2 First\n\n#### H4\n"

        result = runner.invoke(
            cli,
            ["check", "--ignore", "MD001", "--ignore", "MD041", "-"],
            input=content,
        )

        assert result.exit_code == 0
        assert "MD001" not in result.output
        assert "MD041" not in result.output

    def test_check_select_and_ignore_same_rule(self) -> None:
        """When same rule is in both --select and --ignore, ignore wins."""
        runner = CliRunner()
        # Content that triggers MD001 and MD041
        content = "## H2 First\n\n#### H4\n"

        result = runner.invoke(
            cli,
            ["check", "--select", "MD001", "--select", "MD041", "--ignore", "MD041", "-"],
            input=content,
        )

        assert result.exit_code == 1
        assert "MD001" in result.output
        assert "MD041" not in result.output

    def test_check_ignore_unknown_rule(self) -> None:
        """Error when ignoring unknown rule."""
        runner = CliRunner()
        path = fixture_path("cli", "clean.md")

        result = runner.invoke(cli, ["check", "--ignore", "MD999", str(path)])

        assert result.exit_code == 2
        assert "Unknown rule" in result.output
        assert "MD999" in result.output

    def test_check_extend_select_unknown_rule(self) -> None:
        """Error when extend-selecting unknown rule."""
        runner = CliRunner()
        path = fixture_path("cli", "clean.md")

        result = runner.invoke(cli, ["check", "--extend-select", "MD999", str(path)])

        assert result.exit_code == 2
        assert "Unknown rule" in result.output
        assert "MD999" in result.output

    def test_check_extend_ignore_unknown_rule(self) -> None:
        """Error when extend-ignoring unknown rule."""
        runner = CliRunner()
        path = fixture_path("cli", "clean.md")

        result = runner.invoke(cli, ["check", "--extend-ignore", "MD999", str(path)])

        assert result.exit_code == 2
        assert "Unknown rule" in result.output
        assert "MD999" in result.output

    def test_check_ignore_all_rules_clean_exit(self) -> None:
        """Ignoring all rules results in clean exit."""
        runner = CliRunner()
        # Content that would trigger violations (MD001, MD041)
        content = "## H2 First\n\n#### H4\n"

        result = runner.invoke(
            cli,
            [
                "check",
                "--ignore",
                "MD001",
                "--ignore",
                "MD041",
                "-",
            ],
            input=content,
        )

        assert result.exit_code == 0

    def test_check_exclude_file(self, tmp_path) -> None:
        """--exclude omits matching files from results."""
        runner = CliRunner()

        (tmp_path / "keep.md").write_text("# Keep\n")
        (tmp_path / "skip.tmp.md").write_text("# H1\n\n### H3\n")  # Would trigger MD001

        result = runner.invoke(cli, ["check", "--exclude", "*.tmp.md", str(tmp_path)])

        assert result.exit_code == 0
        assert "MD001" not in result.output

    def test_check_exclude_with_show_files(self, tmp_path) -> None:
        """--exclude works with --show-files."""
        runner = CliRunner()

        (tmp_path / "keep.md").write_text("# Keep\n")
        (tmp_path / "skip.tmp.md").write_text("# Skip\n")

        result = runner.invoke(
            cli, ["check", "--show-files", "--exclude", "*.tmp.md", str(tmp_path)]
        )

        assert result.exit_code == 0
        assert "keep.md" in result.output
        assert "skip.tmp.md" not in result.output


class TestCLICheckWithConfig:
    """Integration tests for CLI options interacting with config files."""

    def test_extend_select_adds_to_config(self, tmp_path) -> None:
        """--extend-select adds to config file's select list."""
        runner = CliRunner()

        # Create config with select = ["MD001"]
        config = tmp_path / ".mdlint.toml"
        config.write_text('select = ["MD001"]\n')

        # Create test file that triggers MD001 and MD041
        test_file = tmp_path / "test.md"
        test_file.write_text("## H2 First\n\n#### H4\n")

        result = runner.invoke(
            cli,
            ["check", "--config", str(config), "--extend-select", "MD041", str(test_file)],
        )

        assert result.exit_code == 1
        assert "MD001" in result.output
        assert "MD041" in result.output

    def test_extend_ignore_adds_to_config(self, tmp_path) -> None:
        """--extend-ignore adds to config file's ignore list."""
        runner = CliRunner()

        # Create config with ignore = ["MD001"]
        config = tmp_path / ".mdlint.toml"
        config.write_text('ignore = ["MD001"]\n')

        # Create test file that triggers MD001 and MD041
        test_file = tmp_path / "test.md"
        test_file.write_text("## H2 First\n\n#### H4\n")

        result = runner.invoke(
            cli,
            ["check", "--config", str(config), "--extend-ignore", "MD041", str(test_file)],
        )

        assert result.exit_code == 0
        assert "MD001" not in result.output
        assert "MD041" not in result.output

    def test_extend_ignore_removes_from_selection(self, tmp_path) -> None:
        """--extend-ignore removes rule from config's select list."""
        runner = CliRunner()

        # Create config with select = ["MD001", "MD041"]
        config = tmp_path / ".mdlint.toml"
        config.write_text('select = ["MD001", "MD041"]\n')

        # Create test file that triggers MD001 and MD041
        test_file = tmp_path / "test.md"
        test_file.write_text("## H2 First\n\n#### H4\n")

        result = runner.invoke(
            cli,
            ["check", "--config", str(config), "--extend-ignore", "MD041", str(test_file)],
        )

        assert result.exit_code == 1
        assert "MD001" in result.output
        assert "MD041" not in result.output

    def test_cli_select_overrides_config_select(self, tmp_path) -> None:
        """--select completely replaces config file's select list."""
        runner = CliRunner()

        # Create config with select = ["MD001", "MD041"]
        config = tmp_path / ".mdlint.toml"
        config.write_text('select = ["MD001", "MD041"]\n')

        # Create test file that triggers MD001, MD041, MD003
        test_file = tmp_path / "test.md"
        test_file.write_text("## H2 First\n\n#### H4\n\nHeading\n======\n")

        result = runner.invoke(
            cli, ["check", "--config", str(config), "--select", "MD003", str(test_file)]
        )

        assert result.exit_code == 1
        assert "MD003" in result.output
        assert "MD001" not in result.output
        assert "MD041" not in result.output

    def test_cli_select_with_config_ignore(self, tmp_path) -> None:
        """CLI --select replaces config select, but config ignore still applies."""
        runner = CliRunner()

        # Create config with select = ["MD001"] and ignore = ["MD041"]
        config = tmp_path / ".mdlint.toml"
        config.write_text('select = ["MD001"]\nignore = ["MD041"]\n')

        # Create test file that triggers MD041 and MD003
        test_file = tmp_path / "test.md"
        test_file.write_text("## H2 First\n\nHeading\n======\n")

        # CLI select overrides config select, but config ignore still applies
        result = runner.invoke(
            cli,
            [
                "check",
                "--config",
                str(config),
                "--select",
                "MD041",
                "--select",
                "MD003",
                str(test_file),
            ],
        )

        assert result.exit_code == 1
        assert "MD003" in result.output
        assert "MD041" not in result.output  # Still ignored by config

    def test_config_exclude_omits_files(self, tmp_path) -> None:
        """Config exclude list omits matching files from results."""
        runner = CliRunner()

        config = tmp_path / ".mdlint.toml"
        config.write_text('exclude = ["*.tmp.md"]\n')

        (tmp_path / "keep.md").write_text("# Keep\n")
        (tmp_path / "skip.tmp.md").write_text("# H1\n\n### H3\n")  # Would trigger MD001

        result = runner.invoke(cli, ["check", "--config", str(config), str(tmp_path)])

        assert result.exit_code == 0
        assert "MD001" not in result.output

    def test_config_exclude_directory(self, tmp_path) -> None:
        """Config exclude list omits directory contents."""
        runner = CliRunner()

        subdir = tmp_path / "generated"
        subdir.mkdir()
        (subdir / "out.md").write_text("# H1\n\n### H3\n")  # Would trigger MD001
        (tmp_path / "keep.md").write_text("# Keep\n")

        config = tmp_path / ".mdlint.toml"
        config.write_text(f'exclude = ["{subdir}"]\n')

        result = runner.invoke(cli, ["check", "--config", str(config), str(tmp_path)])

        assert result.exit_code == 0
        assert "MD001" not in result.output

    def test_cli_exclude_overrides_config_exclude(self, tmp_path) -> None:
        """--exclude replaces config exclude list entirely."""
        runner = CliRunner()

        subdir = tmp_path / "generated"
        subdir.mkdir()
        (subdir / "out.md").write_text("# H1\n\n### H3\n")  # Would trigger MD001
        (tmp_path / "keep.md").write_text("# Keep\n")
        (tmp_path / "skip.tmp.md").write_text("# H1\n\n### H3\n")  # Would trigger MD001

        # Config excludes the directory, CLI --exclude replaces with glob pattern
        config = tmp_path / ".mdlint.toml"
        config.write_text(f'exclude = ["{subdir}"]\n')

        result = runner.invoke(
            cli, ["check", "--config", str(config), "--exclude", "*.tmp.md", str(tmp_path)]
        )

        # skip.tmp.md excluded by CLI, but generated/out.md is NOT excluded
        # (CLI replaced config exclude)
        assert result.exit_code == 1
        assert "MD001" in result.output

    def test_extend_exclude_adds_to_config(self, tmp_path) -> None:
        """--extend-exclude adds to config exclude list."""
        runner = CliRunner()

        subdir = tmp_path / "generated"
        subdir.mkdir()
        (subdir / "out.md").write_text("# H1\n\n### H3\n")  # Would trigger MD001
        (tmp_path / "keep.md").write_text("# Keep\n")
        (tmp_path / "skip.tmp.md").write_text("# H1\n\n### H3\n")  # Would trigger MD001

        # Config excludes the directory
        config = tmp_path / ".mdlint.toml"
        config.write_text(f'exclude = ["{subdir}"]\n')

        # --extend-exclude adds glob pattern on top
        result = runner.invoke(
            cli,
            [
                "check",
                "--config",
                str(config),
                "--extend-exclude",
                "*.tmp.md",
                str(tmp_path),
            ],
        )

        # Both generated/out.md and skip.tmp.md are excluded
        assert result.exit_code == 0
        assert "MD001" not in result.output

    def test_extend_exclude_without_config(self, tmp_path) -> None:
        """--extend-exclude works when config has no exclude list."""
        runner = CliRunner()

        (tmp_path / "keep.md").write_text("# Keep\n")
        (tmp_path / "skip.tmp.md").write_text("# H1\n\n### H3\n")  # Would trigger MD001

        result = runner.invoke(cli, ["check", "--extend-exclude", "*.tmp.md", str(tmp_path)])

        assert result.exit_code == 0
        assert "MD001" not in result.output


class TestCLIConfigErrors:
    """Invalid configuration exits 2 with a one-line message instead of a traceback."""

    @pytest.mark.parametrize(
        ("toml", "message"),
        [
            ("[rules.MD013]\nstern = true\n", "rules.MD013.stern: Unknown option"),
            ("[rules.MD013]\nline-length = 100\n", "did you mean line_length?"),
            ("[rules]\nMD013 = false\n", "rules.MD013: Expected a table of options"),
            ("[rules.MD022]\nlines_above = [1,2,1,1,1,1]\n", "Expected an integer"),
            (
                '[rules.MD033]\nallowed_elements = "br, img"\n',
                'write it as allowed_elements = ["br", "img"]',
            ),
            ('[rules.MD029]\nstyle = "one-or-ordered"\n', "rules.MD029.style: Expected one of"),
            ('[rules.MD060]\nstyle = "aligned-no-space"\n', "rules.MD060.style: Expected one of"),
            ("[rules.MD999]\nfoo = 1\n", "rules.MD999: Unknown rule"),
            ('select = ["line-lenght"]\n', "select: Unknown rule(s): line-lenght"),
            ('selct = ["MD001"]\n', "selct: Unknown option"),
            ("[rules.MD013\n", "Invalid TOML"),
        ],
    )
    def test_config_file_error(self, tmp_path, toml: str, message: str) -> None:
        runner = CliRunner()
        config = tmp_path / ".mdlint.toml"
        config.write_text(toml)
        path = fixture_path("cli", "clean.md")

        result = runner.invoke(cli, ["check", "--config", str(config), str(path)])

        assert result.exit_code == 2
        assert result.output.startswith(f"Error: {config}: ")
        assert message in result.output
        assert len(result.output.splitlines()) == 1

    def test_discovered_config_error(self, tmp_path, monkeypatch) -> None:
        """Errors in an automatically discovered config file are reported the same way."""
        runner = CliRunner()
        (tmp_path / ".mdlint.toml").write_text("[rules.MD013]\nstern = true\n")
        monkeypatch.chdir(tmp_path)
        path = fixture_path("cli", "clean.md")

        result = runner.invoke(cli, ["check", str(path)])

        assert result.exit_code == 2
        assert "rules.MD013.stern: Unknown option" in result.output

    def test_inline_config_error(self) -> None:
        runner = CliRunner()
        path = fixture_path("cli", "clean.md")

        result = runner.invoke(cli, ["check", "--config", "MD013.line_length=[", str(path)])

        assert result.exit_code == 2
        assert result.output.startswith("Error: <inline>: Invalid TOML")

    def test_missing_config_file(self) -> None:
        """A --config value without '=' that is not a file is a missing file, not inline TOML."""
        runner = CliRunner()
        path = fixture_path("cli", "clean.md")

        result = runner.invoke(cli, ["check", "--config", "missing.toml", str(path)])

        assert result.exit_code == 2
        assert result.output == "Error: Config file not found: missing.toml\n"

    def test_inline_config_still_applies(self) -> None:
        runner = CliRunner()

        result = runner.invoke(
            cli,
            ["check", "--config", "MD013.line_length=10", "-"],
            input="# T\n\nA long paragraph of text.\n",
        )

        assert result.exit_code == 1
        assert "MD013" in result.output


class TestCLIRuleNames:
    """Rules can be referred to by ID or name, in any case."""

    @pytest.fixture(autouse=True)
    def _no_project_config(self, monkeypatch) -> None:
        monkeypatch.setattr("mdlint.config.find_config_file", lambda start_dir=None: None)

    @pytest.mark.parametrize("flag", ["--select", "--extend-select"])
    @pytest.mark.parametrize("name", ["heading-increment", "md001", "HEADING-INCREMENT"])
    def test_select_by_name(self, flag: str, name: str) -> None:
        runner = CliRunner()

        result = runner.invoke(cli, ["check", flag, name, "-"], input="## H2\n\n#### H4\n")

        assert result.exit_code == 1
        assert "MD001" in result.output

    @pytest.mark.parametrize("flag", ["--ignore", "--extend-ignore"])
    def test_ignore_by_name(self, flag: str) -> None:
        runner = CliRunner()

        result = runner.invoke(
            cli,
            ["check", "--select", "MD001", flag, "heading-increment", "-"],
            input="# H1\n\n### H3\n",
        )

        assert result.exit_code == 0

    def test_config_select_by_name(self, tmp_path) -> None:
        runner = CliRunner()
        config = tmp_path / ".mdlint.toml"
        config.write_text('select = ["line-length"]\n\n[rules.line-length]\nline_length = 10\n')

        result = runner.invoke(
            cli, ["check", "--config", str(config), "-"], input="# T\n\nA long paragraph of text.\n"
        )

        assert result.exit_code == 1
        assert "MD013" in result.output

    def test_config_rule_section_lowercase(self, tmp_path) -> None:
        runner = CliRunner()
        config = tmp_path / ".mdlint.toml"
        config.write_text("[rules.md013]\nline_length = 10\n")

        result = runner.invoke(
            cli, ["check", "--config", str(config), "-"], input="# T\n\nA long paragraph of text.\n"
        )

        assert result.exit_code == 1
        assert "MD013" in result.output


class TestCLIStdin:
    """Tests for reading content from stdin."""

    @pytest.fixture(autouse=True)
    def _no_project_config(self, monkeypatch) -> None:
        monkeypatch.setattr("mdlint.config.find_config_file", lambda start_dir=None: None)

    @pytest.mark.parametrize("fix", [False, True])
    def test_invalid_utf8(self, fix: bool) -> None:
        runner = CliRunner()
        args = ["check", "--fix", "-"] if fix else ["check", "-"]

        result = runner.invoke(cli, args, input=b"# Title\n\ncaf\xe9\n")

        assert result.exit_code == 2
        assert result.output.startswith("Error: <stdin>: ")
        assert len(result.output.splitlines()) == 1

    def test_fix_keeps_crlf_when_stdout_translates_newlines(self, monkeypatch) -> None:
        """Fixed output is written as bytes, so a text-mode stdout cannot double the CRs."""
        content = fixture_path("cli", "clean.md").read_bytes().replace(b"\n", b"\r\n")
        output = io.BytesIO()
        # Text-mode stdout on Windows writes every "\n" as "\r\n".
        stdout = io.TextIOWrapper(output, encoding="utf-8", newline="\r\n", write_through=True)
        monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(content), encoding="utf-8"))
        monkeypatch.setattr(sys, "stdout", stdout)

        with pytest.raises(SystemExit) as exit_info:
            cli.main(["check", "--fix", "-"])

        assert exit_info.value.code == 0
        assert output.getvalue() == content


class TestCLIRule:
    """Integration tests for mdlint rule command."""

    def test_rule_list_all(self) -> None:
        """List all available rules."""
        runner = CliRunner()

        result = runner.invoke(cli, ["rule"])

        assert result.exit_code == 0
        assert "MD001" in result.output
        assert "MD005" in result.output
        assert "heading-increment" in result.output

    def test_rule_single_rule(self) -> None:
        """Show documentation for a single rule."""
        runner = CliRunner()

        result = runner.invoke(cli, ["rule", "MD001"])

        assert result.exit_code == 0
        assert "MD001" in result.output
        assert "heading-increment" in result.output

    def test_rule_single_rule_lowercase(self) -> None:
        """Show documentation for a rule with lowercase ID."""
        runner = CliRunner()

        result = runner.invoke(cli, ["rule", "md001"])

        assert result.exit_code == 0
        assert "MD001" in result.output

    def test_rule_numeric_id(self) -> None:
        """Show documentation for a rule using numeric ID."""
        runner = CliRunner()

        result = runner.invoke(cli, ["rule", "1"])

        assert result.exit_code == 0
        assert "MD001" in result.output
        assert "heading-increment" in result.output

    def test_rule_invalid_id(self) -> None:
        """Error for unknown rule ID."""
        runner = CliRunner()

        result = runner.invoke(cli, ["rule", "MD999"])

        assert result.exit_code == 2
        assert "Unknown rule" in result.output

    def test_rule_unknown_name(self) -> None:
        """Error for a name that matches no rule ID or name."""
        runner = CliRunner()

        result = runner.invoke(cli, ["rule", "foobar"])

        assert result.exit_code == 2
        assert "Unknown rule 'foobar'" in result.output

    @pytest.mark.parametrize("name", ["line-length", "Line-Length"])
    def test_rule_by_name(self, name: str) -> None:
        """Show documentation for a rule looked up by name."""
        runner = CliRunner()

        result = runner.invoke(cli, ["rule", name])

        assert result.exit_code == 0
        assert "MD013: line-length" in result.output

    def test_rule_with_parameters(self) -> None:
        """Show rule with configurable parameters."""
        runner = CliRunner()

        result = runner.invoke(cli, ["rule", "MD003"])

        assert result.exit_code == 0
        assert "MD003" in result.output
        assert "style" in result.output

    def test_rule_shows_parameter_options(self) -> None:
        """Show available options for Literal-typed parameters with descriptions."""
        runner = CliRunner()

        result = runner.invoke(cli, ["rule", "MD003"])

        assert result.exit_code == 0
        assert "default: consistent" in result.output
        # When option_descriptions are provided, options are shown with descriptions
        assert "options:" in result.output
        assert "atx" in result.output
        assert "atx_closed" in result.output
        assert "setext" in result.output
        assert "consistent" in result.output


class TestCLIOutputWidth:
    """Integration tests for how output adapts to the terminal width."""

    @pytest.fixture(autouse=True)
    def _no_project_config(self, monkeypatch) -> None:
        """Prevent tests from picking up the project's .mdlint.toml."""
        monkeypatch.setattr("mdlint.config.find_config_file", lambda start_dir=None: None)

    @pytest.mark.parametrize(
        "args",
        [
            ["--help"],
            ["check", "--help"],
            ["rule", "--help"],
            ["check", "--no-such-option"],
            ["rule", "MD001", "--show-examples"],
        ],
    )
    @pytest.mark.parametrize(("columns", "expected_width"), [(60, 60), (200, 120)])
    def test_boxed_output_fits_terminal_up_to_max_width(
        self, args: list[str], columns: int, expected_width: int
    ) -> None:
        """Help, usage errors and rule docs fit narrow terminals but stop at 120 columns."""
        runner = CliRunner(env={"COLUMNS": str(columns)})

        result = runner.invoke(cli, args)

        assert max(len(line) for line in result.output.splitlines()) == expected_width

    def test_check_results_never_wrapped(self, tmp_path) -> None:
        """Each result stays on one line, so long paths survive narrow terminals and pipes."""
        test_file = tmp_path / ("a-long-directory-name-" * 3) / "document.md"
        test_file.parent.mkdir()
        test_file.write_text(load_fixture("cli", "with_violations.md"))
        runner = CliRunner(env={"COLUMNS": "40"})

        result = runner.invoke(cli, ["check", str(test_file)])

        lines = result.output.splitlines()
        assert f"{test_file} (2)" in lines
        assert "6:1  MD004  List marker style: expected dash, found asterisk" in lines
        assert "✘ Found 2 violations in 1 file (1 file checked)" in lines
