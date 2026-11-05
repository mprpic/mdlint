import pytest
from click.testing import CliRunner

from mdlint.cli import cli
from tests.conftest import load_fixture


class TestCLIFileIO:
    """Integration tests for reading and writing files through the CLI."""

    @pytest.fixture(autouse=True)
    def _no_project_config(self, monkeypatch) -> None:
        """Prevent tests from picking up the project's .mdlint.toml."""
        monkeypatch.setattr("mdlint.config.find_config_file", lambda start_dir=None: None)

    def test_invalid_utf8_reported_and_others_linted(self, tmp_path) -> None:
        """An undecodable file is reported as an error; the rest are still linted."""
        ok_file = tmp_path / "ok.md"
        ok_file.write_text(load_fixture("cli", "clean.md"))
        bad_file = tmp_path / "bad.md"
        bad_file.write_bytes(b"# Title\n\ncaf\xe9\n")

        result = CliRunner().invoke(cli, ["check", str(ok_file), str(bad_file)])

        assert result.exception is None or isinstance(result.exception, SystemExit)
        assert result.exit_code == 2
        assert "bad.md" in result.output
        assert "2 files checked" in result.output

    def test_invalid_utf8_with_fix(self, tmp_path) -> None:
        """--fix also reports an undecodable file as an error and leaves it alone."""
        bad_file = tmp_path / "bad.md"
        bad_file.write_bytes(b"# Title\n\ncaf\xe9 trailing   \n")

        result = CliRunner().invoke(cli, ["check", "--fix", str(bad_file)])

        assert result.exit_code == 2
        assert bad_file.read_bytes() == b"# Title\n\ncaf\xe9 trailing   \n"

    def test_fix_preserves_crlf(self, tmp_path) -> None:
        """--fix writes CRLF files back with CRLF line endings."""
        test_file = tmp_path / "test.md"
        content = load_fixture("linter", "trailing_spaces.md").replace("\n", "\r\n")
        test_file.write_bytes(content.encode("utf-8"))

        result = CliRunner().invoke(cli, ["check", "--fix", str(test_file)])

        assert result.exit_code == 0
        assert test_file.read_bytes() == b"# Title\r\n\r\nTrailing\r\nText\r\n"

    def test_markdown_extension_linted(self, tmp_path) -> None:
        """Files with a .markdown extension are linted."""
        test_file = tmp_path / "README.markdown"
        test_file.write_text(load_fixture("cli", "with_violations.md"))

        result = CliRunner().invoke(cli, ["check", str(test_file)])

        assert result.exit_code == 1
        assert "1 file checked" in result.output
