from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md047 import MD047, MD047Config
from tests.conftest import load_fixture


class TestMD047:
    @pytest.fixture
    def rule(self) -> MD047:
        return MD047()

    @pytest.fixture
    def config(self) -> MD047Config:
        return MD047Config()

    def test_valid_document(self, rule: MD047, config: MD047Config) -> None:
        """Valid document passes the rule."""
        content = load_fixture("md047", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD047, config: MD047Config) -> None:
        """Invalid document triggers violations."""
        content = load_fixture("md047", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD047"
        assert violations[0].line == 3
        assert "newline" in violations[0].message.lower()

    def test_file_ending_with_newline(self, rule: MD047, config: MD047Config) -> None:
        """File ending with a single newline is valid."""
        content = "# Heading\n\nSome text.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_file_not_ending_with_newline(self, rule: MD047, config: MD047Config) -> None:
        """File not ending with a newline is a violation."""
        content = "# Heading\n\nSome text."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3
        assert violations[0].column == 11

    def test_file_ending_with_multiple_newlines(self, rule: MD047, config: MD047Config) -> None:
        """File ending with multiple newlines is valid for MD047."""
        content = "# Heading\n\nSome text.\n\n\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        # MD047 only checks for missing newline, not multiple newlines
        assert len(violations) == 0

    def test_empty_file(self, rule: MD047, config: MD047Config) -> None:
        """Empty file is valid."""
        content = ""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_only_newline(self, rule: MD047, config: MD047Config) -> None:
        """File with only a newline is valid."""
        content = "\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_single_character_no_newline(self, rule: MD047, config: MD047Config) -> None:
        """Single character without trailing newline triggers violation."""
        content = "x"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert violations[0].column == 2

    def test_column_at_end_of_line(self, rule: MD047, config: MD047Config) -> None:
        """Column should be at the end of the last line (where newline should be)."""
        content = "Hello"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].column == 6  # After "Hello"

    def test_whitespace_only_line_no_newline(self, rule: MD047, config: MD047Config) -> None:
        """Line with only whitespace and no trailing newline triggers violation."""
        content = "# Heading\n   "
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 2
        assert violations[0].column == 4

    def test_violation_message(self, rule: MD047, config: MD047Config) -> None:
        """Violation message describes the issue."""
        content = "No newline at end"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "newline" in violations[0].message.lower()
        assert "end" in violations[0].message.lower()

    def test_fix_corrects_invalid(self, rule: MD047, config: MD047Config) -> None:
        """Fixing invalid document adds trailing newline."""
        content = load_fixture("md047", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert result.endswith("\n")
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_returns_none_for_valid(self, rule: MD047, config: MD047Config) -> None:
        """Fixing valid document returns None."""
        content = load_fixture("md047", "valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_empty_file(self, rule: MD047, config: MD047Config) -> None:
        """Fixing empty file returns None."""
        doc = Document(Path("test.md"), "")
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_single_character_no_newline(self, rule: MD047, config: MD047Config) -> None:
        """Fixing single character without newline appends one."""
        doc = Document(Path("test.md"), "x")
        result = rule.fix(doc, config)
        assert result == "x\n"

    def test_fix_preserves_multiple_trailing_newlines(
        self, rule: MD047, config: MD047Config
    ) -> None:
        """Fixing already-valid file with multiple trailing newlines returns None."""
        doc = Document(Path("test.md"), "# Heading\n\n\n")
        result = rule.fix(doc, config)
        assert result is None
