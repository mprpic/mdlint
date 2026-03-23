from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md011 import MD011, MD011Config
from tests.conftest import load_fixture


class TestMD011:
    @pytest.fixture
    def rule(self) -> MD011:
        return MD011()

    @pytest.fixture
    def config(self) -> MD011Config:
        return MD011Config()

    def test_valid_document(self, rule: MD011, config: MD011Config) -> None:
        """Valid document with correct link syntax passes the rule."""
        content = load_fixture("md011", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD011, config: MD011Config) -> None:
        """Invalid document with reversed link syntax triggers violations."""
        content = load_fixture("md011", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD011"
        assert violations[0].rule_name == "no-reversed-links"
        assert "reversed" in violations[0].message.lower()

    def test_reversed_link_detection(self, rule: MD011, config: MD011Config) -> None:
        """Reversed link syntax is detected correctly."""
        content = "(link text)[https://example.com/]"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert violations[0].column == 1

    def test_column_position_reported(self, rule: MD011, config: MD011Config) -> None:
        """Column position is correctly reported."""
        content = "Some text (link)[https://example.com/] more text"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert violations[0].column == 11  # Position after "Some text "

    def test_multiple_reversed_links_on_same_line(self, rule: MD011, config: MD011Config) -> None:
        """Multiple reversed links on the same line are reported."""
        content = "(first)[https://first.com/] and (second)[https://second.com/]"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].column == 1
        assert violations[1].column == 33

    def test_code_blocks_ignored(self, rule: MD011, config: MD011Config) -> None:
        """Reversed links in code blocks are ignored."""
        content = load_fixture("md011", "code_blocks.md")
        doc = Document(Path("code_blocks.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_inline_code_ignored(self, rule: MD011, config: MD011Config) -> None:
        """Reversed links in inline code are ignored."""
        content = "Use `(text)[link]` for reversed syntax example."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_footnotes_allowed(self, rule: MD011, config: MD011Config) -> None:
        """Footnote syntax does not trigger the rule."""
        content = load_fixture("md011", "footnotes.md")
        doc = Document(Path("footnotes.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_footnote_with_caret(self, rule: MD011, config: MD011Config) -> None:
        """Footnote references starting with caret are allowed."""
        content = "For (example)[^1] and (another)[^note]"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_empty_document(self, rule: MD011, config: MD011Config) -> None:
        """Empty document has no violations."""
        content = ""
        doc = Document(Path("empty.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_context_includes_line_content(self, rule: MD011, config: MD011Config) -> None:
        """Violation context includes the full line content."""
        content = "Bad link: (text)[https://example.com/]"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].context == content

    def test_escaped_parentheses_not_matched(self, rule: MD011, config: MD011Config) -> None:
        """Escaped parentheses should not trigger the rule."""
        content = r"\(not a link\)[text]"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_nested_parentheses_not_matched(self, rule: MD011, config: MD011Config) -> None:
        """Nested parentheses in link text are not matched (limitation)."""
        # This is consistent with reference implementations that use [^()]+ pattern
        content = "(link with (parens))[https://example.com/]"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        # Nested parentheses are not caught (limitation of regex approach)
        assert len(violations) == 0

    def test_backslash_ending_link_text_not_matched(self, rule: MD011, config: MD011Config) -> None:
        """Link text ending with backslash should not trigger the rule."""
        content = r"(text\)[url]"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_backslash_ending_destination_not_matched(
        self, rule: MD011, config: MD011Config
    ) -> None:
        """Link destination ending with backslash should not trigger the rule."""
        content = r"(text)[url\]"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_inline_code_with_double_backticks(self, rule: MD011, config: MD011Config) -> None:
        """Reversed links in double-backtick inline code are ignored."""
        content = "Use ``(text)[link]`` for reversed syntax example."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_fix_corrects_invalid(self, rule: MD011, config: MD011Config) -> None:
        """Fix converts reversed link syntax to correct syntax."""
        content = load_fixture("md011", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        # Verify the fixed content has no violations
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []
        # Verify specific corrections
        assert "[incorrect link syntax](https://www.example.com/)" in result
        assert "[another bad link](https://example.org/page)" in result

    def test_fix_returns_none_for_valid(self, rule: MD011, config: MD011Config) -> None:
        """Fix returns None when there are no reversed links."""
        content = load_fixture("md011", "valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_preserves_code_blocks(self, rule: MD011, config: MD011Config) -> None:
        """Fix does not modify reversed links inside code blocks."""
        content = load_fixture("md011", "code_blocks.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_preserves_footnotes(self, rule: MD011, config: MD011Config) -> None:
        """Fix does not modify footnote syntax."""
        content = load_fixture("md011", "footnotes.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_multiple_on_same_line(self, rule: MD011, config: MD011Config) -> None:
        """Fix corrects multiple reversed links on the same line."""
        content = "(first)[https://first.com/] and (second)[https://second.com/]"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert result == "[first](https://first.com/) and [second](https://second.com/)"

    def test_fix_preserves_inline_code(self, rule: MD011, config: MD011Config) -> None:
        """Fix does not modify reversed links inside inline code."""
        content = "Use `(text)[link]` for reversed syntax example."
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_html_blocks_ignored(self, rule: MD011, config: MD011Config) -> None:
        """Reversed link patterns inside HTML blocks are ignored."""
        content = load_fixture("md011", "html_blocks.md")
        doc = Document(Path("html_blocks.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_fix_preserves_html_blocks(self, rule: MD011, config: MD011Config) -> None:
        """Fix does not modify reversed link patterns inside HTML blocks."""
        content = load_fixture("md011", "html_blocks.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_empty_document(self, rule: MD011, config: MD011Config) -> None:
        """Fix returns None for empty document."""
        doc = Document(Path("test.md"), "")
        result = rule.fix(doc, config)
        assert result is None
