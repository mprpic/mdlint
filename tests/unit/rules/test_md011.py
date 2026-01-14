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
