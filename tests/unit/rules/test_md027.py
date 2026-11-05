from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.linter import Linter
from mdlint.rules.md027 import MD027, MD027Config
from tests.conftest import load_fixture


class TestMD027:
    @pytest.fixture
    def rule(self) -> MD027:
        return MD027()

    @pytest.fixture
    def config(self) -> MD027Config:
        return MD027Config()

    def test_valid_document(self, rule: MD027, config: MD027Config) -> None:
        """Valid document with single space after blockquote marker passes."""
        content = load_fixture("md027", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD027, config: MD027Config) -> None:
        """Invalid document with multiple spaces triggers violations."""
        content = load_fixture("md027", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD027"
        assert violations[0].line == 1
        assert violations[1].line == 2

    def test_no_blockquotes(self, rule: MD027, config: MD027Config) -> None:
        """Document without blockquotes passes."""
        doc = Document(Path("no_blockquotes.md"), "# Heading\n\nSome text.\n")

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_nested_blockquote(self, rule: MD027, config: MD027Config) -> None:
        """Nested blockquotes with multiple spaces are detected."""
        content = "> Outer quote\n>>  Inner quote with extra space\n"
        doc = Document(Path("nested.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 2

    def test_empty_blockquote(self, rule: MD027, config: MD027Config) -> None:
        """Empty blockquote lines pass."""
        content = ">\n> Some text\n>\n"
        doc = Document(Path("empty.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_indented_code_block_in_blockquote(self, rule: MD027, config: MD027Config) -> None:
        """Indented code blocks inside blockquotes are not flagged."""
        content = "> Some text:\n>\n>     indented code\n>     more code\n>\n> Back to normal\n"
        doc = Document(Path("code_block.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_blockquote_with_heading(self, rule: MD027, config: MD027Config) -> None:
        """Blockquote containing a heading does not trigger violations."""
        content = "> # Heading\n>\n> Some text\n"
        doc = Document(Path("heading.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_blockquote_with_list(self, rule: MD027, config: MD027Config) -> None:
        """Blockquote containing a list does not trigger violations."""
        content = "> - Item 1\n> - Item 2\n> - Item 3\n"
        doc = Document(Path("list.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_nested_list_in_blockquote(self, rule: MD027, config: MD027Config) -> None:
        """Indentation that belongs to a list item inside the blockquote is not flagged."""
        content = load_fixture("md027", "list_in_blockquote.md")
        doc = Document(Path("list_in_blockquote.md"), content)

        assert rule.check(doc, config) == []
        assert rule.fix(doc, config) is None

    def test_nested_blockquote_with_space(self, rule: MD027, config: MD027Config) -> None:
        """Extra space after the inner marker of space-separated nested quotes is detected."""
        content = load_fixture("md027", "nested_blockquote.md")
        doc = Document(Path("nested_blockquote.md"), content)

        violations = rule.check(doc, config)

        assert [(v.line, v.column) for v in violations] == [(2, 4)]

    def test_html_block(self, rule: MD027, config: MD027Config) -> None:
        """A ``>`` inside an HTML block is literal text, not a blockquote."""
        content = load_fixture("md027", "html_block.md")
        doc = Document(Path("html_block.md"), content)

        assert rule.check(doc, config) == []

    def test_paragraph_continuation(self, rule: MD027, config: MD027Config) -> None:
        """Deeply indented paragraph continuation lines are still reported."""
        content = load_fixture("md027", "paragraph_continuation.md")
        doc = Document(Path("paragraph_continuation.md"), content)

        violations = rule.check(doc, config)

        assert [v.line for v in violations] == [1, 2]

    def test_violation_details(self, rule: MD027, config: MD027Config) -> None:
        """Violation includes correct details."""
        content = load_fixture("md027", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert violations[0].rule_id == "MD027"
        assert violations[0].rule_name == "no-multiple-space-blockquote"
        assert ">  This is a blockquote" in violations[0].context

    def test_fix_corrects_invalid(self, rule: MD027, config: MD027Config) -> None:
        """Fix collapses multiple spaces to one after blockquote marker."""
        content = load_fixture("md027", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_returns_none_for_valid(self, rule: MD027, config: MD027Config) -> None:
        """Fix returns None when content is already valid."""
        content = load_fixture("md027", "valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_nested_blockquote(self, rule: MD027, config: MD027Config) -> None:
        """Fix corrects nested blockquotes with multiple spaces."""
        content = "> Outer quote\n>>  Inner quote with extra space\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert result == "> Outer quote\n>> Inner quote with extra space\n"

    def test_fix_preserves_code_blocks(self, rule: MD027, config: MD027Config) -> None:
        """Fix does not modify content inside code blocks."""
        content = "> Some text:\n>\n>     indented code\n>     more code\n>\n> Back to normal\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_produces_expected_output(self, rule: MD027, config: MD027Config) -> None:
        """Fix of invalid fixture produces correct spacing."""
        invalid = load_fixture("md027", "invalid.md")
        doc = Document(Path("test.md"), invalid)
        result = rule.fix(doc, config)
        expected = "> This is a blockquote with bad indentation\n> there should only be one.\n"
        assert result == expected

    def test_fix_nested_blockquote_with_space(self, rule: MD027, config: MD027Config) -> None:
        """Fix collapses the space after the inner marker of nested quotes."""
        content = load_fixture("md027", "nested_blockquote.md")
        result = rule.fix(Document(Path("test.md"), content), config)
        assert result == "> Outer quote\n> > Inner quote with extra space\n"

    def test_fix_declines_when_text_would_start_a_block(
        self, rule: MD027, config: MD027Config
    ) -> None:
        """Fix leaves a continuation line alone if removing its indent would change the block."""
        content = load_fixture("md027", "paragraph_continuation.md")
        result = rule.fix(Document(Path("test.md"), content), config)
        assert result == "> Paragraph with extra space\n>     ---\n"

    @pytest.mark.parametrize(
        "filename", ["invalid.md", "nested_blockquote.md", "paragraph_continuation.md"]
    )
    def test_fix_is_idempotent(self, rule: MD027, config: MD027Config, filename: str) -> None:
        """Fixing an already fixed document changes nothing."""
        content = load_fixture("md027", filename)
        once = rule.fix(Document(Path("test.md"), content), config)
        assert once is not None
        assert rule.fix(Document(Path("test.md"), once), config) is None


class TestListIndentRulesAgree:
    """MD005, MD007 and MD027 must not undo each other's work on lists in blockquotes."""

    @pytest.mark.parametrize(
        ("rule_id", "filename"),
        [("md027", "list_in_blockquote.md"), ("md007", "blockquote_in_list.md")],
    )
    def test_fix_leaves_valid_list_unchanged(self, rule_id: str, filename: str) -> None:
        """Running the three fixes together keeps a valid list in a blockquote as is."""
        content = load_fixture(rule_id, filename)
        linter = Linter(enabled_rules={"MD005", "MD007", "MD027"})

        result, fixed = linter.fix_stdin(content)

        assert fixed == content
        assert result.violations == []
