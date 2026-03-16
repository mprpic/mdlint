from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md038 import MD038, MD038Config
from tests.conftest import load_fixture


class TestMD038:
    @pytest.fixture
    def rule(self) -> MD038:
        return MD038()

    @pytest.fixture
    def config(self) -> MD038Config:
        return MD038Config()

    def test_valid_document(self, rule: MD038, config: MD038Config) -> None:
        """Valid document passes the rule."""
        content = load_fixture("md038", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD038, config: MD038Config) -> None:
        """Invalid document triggers violations."""
        content = load_fixture("md038", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 4
        assert violations[0].rule_id == "MD038"
        assert violations[0].rule_name == "no-space-in-code"

    def test_leading_space(self, rule: MD038, config: MD038Config) -> None:
        """Code span with leading space triggers violation."""
        content = "Text with ` leading space` here."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "leading" in violations[0].message.lower()

    def test_trailing_space(self, rule: MD038, config: MD038Config) -> None:
        """Code span with trailing space triggers violation."""
        content = "Text with `trailing space ` here."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "trailing" in violations[0].message.lower()

    def test_symmetric_single_space_padding(self, rule: MD038, config: MD038Config) -> None:
        """Symmetric single-space padding is valid per CommonMark spec."""
        content = "Text with ` both sides ` here."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_double_space_both_sides(self, rule: MD038, config: MD038Config) -> None:
        """Code span with double spaces on both sides triggers violations."""
        content = "Text with `  both sides  ` here."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2

    def test_double_backticks_with_padding(self, rule: MD038, config: MD038Config) -> None:
        """Double backtick code spans with single space padding are valid."""
        content = "Code with `` `backticks` `` inside."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_double_backtick_padding_without_backticks(
        self, rule: MD038, config: MD038Config
    ) -> None:
        """Double backtick code spans with padding but no embedded backticks are valid."""
        content = "Code with `` code `` inside."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_proper_code_span(self, rule: MD038, config: MD038Config) -> None:
        """Properly formatted code span has no violations."""
        content = "Text with `proper code` here."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_empty_document(self, rule: MD038, config: MD038Config) -> None:
        """Empty document has no violations."""
        content = ""
        doc = Document(Path("empty.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_no_code_spans(self, rule: MD038, config: MD038Config) -> None:
        """Document without code spans has no violations."""
        content = "# Heading\n\nSome regular text."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_code_block_not_checked(self, rule: MD038, config: MD038Config) -> None:
        """Fenced code blocks are not checked."""
        content = "```\n` leading space`\n```"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_spaces(self, rule: MD038, config: MD038Config) -> None:
        """Multiple spaces at start/end trigger violations."""
        content = "Text with `   multiple spaces   ` here."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2

    def test_column_position_leading(self, rule: MD038, config: MD038Config) -> None:
        """Column position is correctly reported for leading space."""
        content = "A ` code` B"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        # Column should point to the space after the backtick
        assert violations[0].column == 4

    def test_column_position_trailing(self, rule: MD038, config: MD038Config) -> None:
        """Column position is correctly reported for trailing space."""
        content = "A `code ` B"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        # Column should point to the trailing space
        assert violations[0].column == 8

    def test_column_position_with_padding(self, rule: MD038, config: MD038Config) -> None:
        """Column positions account for stripped padding space."""
        content = "`  code  `"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        # Leading: padding space at col 2, violation space at col 3
        assert violations[0].column == 3
        # Trailing: violation space at col 8 (before padding space at col 9)
        assert violations[1].column == 8

    def test_multiple_code_spans_on_line(self, rule: MD038, config: MD038Config) -> None:
        """Multiple code spans on same line are all checked."""
        content = "Both `  bad  ` and `  also bad  ` here."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 4  # 2 per code span

    def test_space_only_content_valid(self, rule: MD038, config: MD038Config) -> None:
        """Code span with only spaces is valid (per CommonMark spec)."""
        content = "Text with `   ` here."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_single_space_content_valid(self, rule: MD038, config: MD038Config) -> None:
        """Code span with single space is valid."""
        content = "Text with ` ` here."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_tab_leading(self, rule: MD038, config: MD038Config) -> None:
        """Tab as leading whitespace triggers violation."""
        content = "Text with `\tcode` here."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "leading" in violations[0].message.lower()

    def test_tab_trailing(self, rule: MD038, config: MD038Config) -> None:
        """Tab as trailing whitespace triggers violation."""
        content = "Text with `code\t` here."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "trailing" in violations[0].message.lower()

    def test_fix_corrects_invalid(self, rule: MD038, config: MD038Config) -> None:
        """Fixing invalid content removes spaces from code spans."""
        content = load_fixture("md038", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_returns_none_for_valid(self, rule: MD038, config: MD038Config) -> None:
        """Fixing already-valid content returns None."""
        content = load_fixture("md038", "valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_leading_space(self, rule: MD038, config: MD038Config) -> None:
        """Fix removes leading space from code span."""
        content = "Text with ` code` here."
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result == "Text with `code` here."

    def test_fix_trailing_space(self, rule: MD038, config: MD038Config) -> None:
        """Fix removes trailing space from code span."""
        content = "Text with `code ` here."
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result == "Text with `code` here."

    def test_fix_both_sides_with_padding(self, rule: MD038, config: MD038Config) -> None:
        """Fix removes extra spaces but preserves symmetric padding."""
        content = "Text with `  code  ` here."
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result == "Text with ` code ` here."

    def test_fix_multiple_code_spans(self, rule: MD038, config: MD038Config) -> None:
        """Fix handles multiple code spans on same line."""
        content = "Both `  bad  ` and `  also bad  ` here."
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_skips_code_blocks(self, rule: MD038, config: MD038Config) -> None:
        """Fix does not modify content inside code blocks."""
        content = "```\n` leading space`\n```"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_whitespace_only_unchanged(self, rule: MD038, config: MD038Config) -> None:
        """Fix does not modify code spans containing only whitespace."""
        content = "Text with `   ` here."
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_tabs(self, rule: MD038, config: MD038Config) -> None:
        """Fix removes tab whitespace from code spans."""
        content = "Text with `\tcode\t` here."
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result == "Text with `code` here."
