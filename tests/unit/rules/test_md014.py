from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md014 import MD014, MD014Config
from tests.conftest import load_fixture


class TestMD014:
    @pytest.fixture
    def rule(self) -> MD014:
        return MD014()

    @pytest.fixture
    def config(self) -> MD014Config:
        return MD014Config()

    def test_valid_document(self, rule: MD014, config: MD014Config) -> None:
        """Valid document passes the rule."""
        content = load_fixture("md014", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD014, config: MD014Config) -> None:
        """Invalid document triggers violations."""
        content = load_fixture("md014", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 3
        assert violations[0].rule_id == "MD014"
        assert violations[0].rule_name == "commands-show-output"
        assert "dollar sign" in violations[0].message.lower()
        assert "output" in violations[0].message.lower()
        assert violations[0].line == 6
        assert violations[1].line == 7
        assert violations[2].line == 8

    def test_mixed_output_is_valid(self, rule: MD014, config: MD014Config) -> None:
        """Code blocks with some commands showing output are valid."""
        content = load_fixture("md014", "mixed_output.md")
        doc = Document(Path("mixed_output.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_indented_code_block(self, rule: MD014, config: MD014Config) -> None:
        """Indented code blocks are also checked."""
        content = load_fixture("md014", "indented_code.md")
        doc = Document(Path("indented_code.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 3
        assert violations[0].line == 5
        assert violations[1].line == 6
        assert violations[2].line == 7

    def test_empty_code_block(self, rule: MD014, config: MD014Config) -> None:
        """Empty code blocks are valid."""
        content = load_fixture("md014", "empty_code_block.md")
        doc = Document(Path("empty_code_block.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_no_code_blocks(self, rule: MD014, config: MD014Config) -> None:
        """Document without code blocks has no violations."""
        content = "# Heading\n\nSome regular text."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_column_position(self, rule: MD014, config: MD014Config) -> None:
        """Dollar sign position is correctly reported."""
        content = "```\n$ ls\n```"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 2
        assert violations[0].column == 1

    def test_indented_dollar_sign(self, rule: MD014, config: MD014Config) -> None:
        """Indented dollar signs are detected."""
        content = "```\n  $ ls\n  $ cat\n```"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].column == 3  # After two spaces

    def test_dollar_without_space_not_matched(self, rule: MD014, config: MD014Config) -> None:
        """Dollar signs without trailing space are not matched."""
        content = "```\n$PATH\n$HOME\n```"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_empty_document(self, rule: MD014, config: MD014Config) -> None:
        """Empty document has no violations."""
        content = ""
        doc = Document(Path("empty.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_single_dollar_command(self, rule: MD014, config: MD014Config) -> None:
        """A single dollar command without output is a violation."""
        content = "```\n$ ls\n```\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 2
        assert violations[0].column == 1

    def test_multiple_code_blocks(self, rule: MD014, config: MD014Config) -> None:
        """Only code blocks where all lines have $ are flagged."""
        content = "```\n$ ls\n$ cat foo\n```\n\n```\n$ ls\nfoo bar\n$ cat baz\nqux\n```\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        # First block: all lines have $ → 2 violations
        # Second block: has output lines → no violations
        assert len(violations) == 2
        assert violations[0].line == 2
        assert violations[1].line == 3

    def test_blank_lines_between_commands(self, rule: MD014, config: MD014Config) -> None:
        """Blank lines between dollar commands don't break the check."""
        content = "```\n$ ls\n\n$ cat foo\n```\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        # Blank lines are ignored; all non-empty lines have $ → violations
        assert len(violations) == 2
        assert violations[0].line == 2
        assert violations[1].line == 4


class TestMD014Fix:
    @pytest.fixture
    def rule(self) -> MD014:
        return MD014()

    @pytest.fixture
    def config(self) -> MD014Config:
        return MD014Config()

    def test_fix_returns_none_for_valid(self, rule: MD014, config: MD014Config) -> None:
        """Fixing already-valid content returns None."""
        content = load_fixture("md014", "valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_corrects_invalid(self, rule: MD014, config: MD014Config) -> None:
        """Fixing invalid content removes dollar sign prefixes."""
        content = load_fixture("md014", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        # Verify fixed content has no violations
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []
        # Verify the commands are preserved without dollar signs
        assert "ls\n" in result
        assert "cat foo\n" in result
        assert "less bar\n" in result

    def test_fix_indented_code_block(self, rule: MD014, config: MD014Config) -> None:
        """Fixing indented code blocks removes dollar sign prefixes."""
        content = load_fixture("md014", "indented_code.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_mixed_output_unchanged(self, rule: MD014, config: MD014Config) -> None:
        """Code blocks with output are not modified."""
        content = load_fixture("md014", "mixed_output.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_multiple_code_blocks(self, rule: MD014, config: MD014Config) -> None:
        """Only code blocks where all lines have $ are fixed."""
        content = "```\n$ ls\n$ cat foo\n```\n\n```\n$ ls\nfoo bar\n$ cat baz\nqux\n```\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        # First block fixed, second block unchanged
        assert "```\nls\ncat foo\n```" in result
        assert "$ ls\nfoo bar\n$ cat baz\nqux" in result

    def test_fix_blank_lines_between_commands(self, rule: MD014, config: MD014Config) -> None:
        """Blank lines between commands are preserved."""
        content = "```\n$ ls\n\n$ cat foo\n```\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert "```\nls\n\ncat foo\n```" in result

    def test_fix_indented_dollar_signs(self, rule: MD014, config: MD014Config) -> None:
        """Indented dollar signs are fixed, preserving indentation."""
        content = "```\n  $ ls\n  $ cat\n```"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert "```\n  ls\n  cat\n```" in result
