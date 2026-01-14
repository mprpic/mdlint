from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md028 import MD028, MD028Config
from tests.conftest import load_fixture


class TestMD028:
    @pytest.fixture
    def rule(self) -> MD028:
        return MD028()

    @pytest.fixture
    def config(self) -> MD028Config:
        return MD028Config()

    def test_valid_document(self, rule: MD028, config: MD028Config) -> None:
        """Valid document passes the rule."""
        content = load_fixture("md028", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD028, config: MD028Config) -> None:
        """Invalid document triggers violations."""
        content = load_fixture("md028", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD028"
        assert violations[0].line == 3
        assert "blank" in violations[0].message.lower()

    def test_continued_blockquote_valid(self, rule: MD028, config: MD028Config) -> None:
        """Blockquotes with > on blank lines are valid (same blockquote)."""
        content = load_fixture("md028", "continued_blockquote.md")
        doc = Document(Path("continued_blockquote.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_no_blockquotes(self, rule: MD028, config: MD028Config) -> None:
        """Document without blockquotes passes."""
        content = "# Heading\n\nSome text here.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_single_blockquote(self, rule: MD028, config: MD028Config) -> None:
        """Single blockquote passes."""
        content = "> This is a blockquote.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_blank_lines_between_blockquotes(
        self, rule: MD028, config: MD028Config
    ) -> None:
        """Multiple blank lines between blockquotes trigger multiple violations."""
        content = "> First blockquote\n\n\n> Second blockquote\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        # Each blank line between blockquotes is a violation
        assert len(violations) == 2
        assert violations[0].line == 2
        assert violations[1].line == 3

    def test_blockquote_with_text_between(self, rule: MD028, config: MD028Config) -> None:
        """Blockquotes separated by text are valid."""
        content = "> First blockquote\n\nSome text\n\n> Second blockquote\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_separate_violations(self, rule: MD028, config: MD028Config) -> None:
        """Multiple separate blank line violations in document."""
        content = "> Quote 1\n\n> Quote 2\n\n> Quote 3\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 2
        assert violations[1].line == 4

    def test_nested_blockquotes(self, rule: MD028, config: MD028Config) -> None:
        """Nested blockquotes with proper continuation are valid."""
        content = "> Outer\n> > Inner\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_column_is_one(self, rule: MD028, config: MD028Config) -> None:
        """Column should always be 1 for blank line violations."""
        content = "> First\n\n> Second\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].column == 1

    def test_fenced_code_block_no_false_positive(self, rule: MD028, config: MD028Config) -> None:
        """Lines starting with > inside fenced code blocks are not blockquotes."""
        content = load_fixture("md028", "fenced_code_block.md")
        doc = Document(Path("fenced_code_block.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_indented_code_block_no_false_positive(self, rule: MD028, config: MD028Config) -> None:
        """Lines starting with > inside indented code blocks are not blockquotes."""
        content = load_fixture("md028", "indented_code_block.md")
        doc = Document(Path("indented_code_block.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_blockquotes_inside_list_item(self, rule: MD028, config: MD028Config) -> None:
        """Blockquotes inside list items separated by blank line trigger violation."""
        content = load_fixture("md028", "list_blockquotes.md")
        doc = Document(Path("list_blockquotes.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 4
