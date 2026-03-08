import json

import pytest
from click.testing import CliRunner

from mdlint.cli import cli
from tests.conftest import fixture_path


class TestCLIFix:
    """Integration tests for --fix flag on the check command."""

    @pytest.fixture(autouse=True)
    def _no_project_config(self, monkeypatch) -> None:
        """Prevent tests from picking up the project's .mdlint.toml."""
        monkeypatch.setattr("mdlint.config.find_config_file", lambda start_dir=None: None)

    def test_fix_flag_accepted(self) -> None:
        """--fix flag is accepted without error."""
        runner = CliRunner()
        path = fixture_path("cli", "clean.md")

        result = runner.invoke(cli, ["check", "--fix", str(path)])

        assert result.exit_code == 0

    def test_fix_no_fixable_rules(self) -> None:
        """--fix with no fixable rules still reports violations."""
        runner = CliRunner()
        path = fixture_path("cli", "with_violations.md")

        result = runner.invoke(cli, ["check", "--fix", str(path)])

        assert result.exit_code == 1

    def test_fix_stdin_outputs_content(self) -> None:
        """--fix with stdin outputs the (unchanged) content to stdout."""
        runner = CliRunner()
        content = "# Valid heading\n\nSome content.\n"

        result = runner.invoke(cli, ["check", "--fix", "-"], input=content)

        assert result.exit_code == 0
        assert result.output == content

    def test_fix_stdin_with_violations(self) -> None:
        """--fix with stdin and unfixable violations exits with code 1."""
        runner = CliRunner()
        content = "# H1\n\n### H3\n"

        result = runner.invoke(cli, ["check", "--fix", "-"], input=content)

        assert result.exit_code == 1
        # Content is still output even with violations
        assert content in result.output

    def test_fix_json_output_includes_files_fixed(self) -> None:
        """JSON output includes files_fixed in summary."""
        runner = CliRunner()
        path = fixture_path("cli", "clean.md")

        result = runner.invoke(cli, ["check", "--fix", "--format", "json", str(path)])

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert "files_fixed" in output["summary"]
        assert output["summary"]["files_fixed"] == 0

    def test_fix_file_not_modified_when_no_fixable_rules(self, tmp_path) -> None:
        """--fix does not modify files when no rules are fixable."""
        runner = CliRunner()
        test_file = tmp_path / "test.md"
        original = "# Heading\n\nSome content.\n"
        test_file.write_text(original)

        result = runner.invoke(cli, ["check", "--fix", str(test_file)])

        assert result.exit_code == 0
        assert test_file.read_text() == original
