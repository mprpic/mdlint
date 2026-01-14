from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md012 import MD012, MD012Config
from tests.conftest import load_fixture


class TestMD012:
    @pytest.fixture
    def rule(self) -> MD012:
        return MD012()

    @pytest.fixture
    def config(self) -> MD012Config:
        return MD012Config()

    def test_valid_document(self, rule: MD012, config: MD012Config) -> None:
        """Valid document passes the rule."""
        content = load_fixture("md012", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD012, config: MD012Config) -> None:
        """Invalid document triggers violations."""
        content = load_fixture("md012", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD012"
        assert violations[0].line == 5
        assert "blank" in violations[0].message.lower()

    def test_code_block_ignored(self, rule: MD012, config: MD012Config) -> None:
        """Multiple blank lines inside code blocks are allowed."""
        content = load_fixture("md012", "code_block_valid.md")
        doc = Document(Path("code_block_valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_consecutive_blanks(self, rule: MD012, config: MD012Config) -> None:
        """Multiple consecutive blank lines trigger violations."""
        content = "# Heading\n\n\n\nText\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        # Lines 3 and 4 are extra blank lines (beyond 1 allowed)
        assert len(violations) == 2
        assert violations[0].line == 3
        assert violations[1].line == 4

    def test_maximum_config_two(self, rule: MD012) -> None:
        """Maximum of 2 allows two consecutive blank lines."""
        config = MD012Config(maximum=2)
        content = "# Heading\n\n\nText\n"  # Two blank lines
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_maximum_config_two_violated(self, rule: MD012) -> None:
        """Maximum of 2 is violated by three blank lines."""
        config = MD012Config(maximum=2)
        content = "# Heading\n\n\n\nText\n"  # Three blank lines
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 4

    def test_indented_code_block_ignored(self, rule: MD012, config: MD012Config) -> None:
        """Multiple blank lines inside indented code blocks are allowed."""
        content = "# Heading\n\n    code line 1\n\n\n    code line 2\n\nText\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_blank_at_start(self, rule: MD012, config: MD012Config) -> None:
        """Multiple blank lines at start of document."""
        content = "\n\n# Heading\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 2

    def test_blank_at_end(self, rule: MD012, config: MD012Config) -> None:
        """Multiple blank lines at end of document."""
        content = "# Heading\n\n\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3

    def test_single_blank_line_allowed(self, rule: MD012, config: MD012Config) -> None:
        """Single blank lines are allowed throughout."""
        content = "# Heading\n\nPara 1\n\nPara 2\n\nPara 3\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_violations_in_document(self, rule: MD012, config: MD012Config) -> None:
        """Multiple separate violations in the document."""
        content = "# Heading\n\n\nPara 1\n\n\nPara 2\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 3
        assert violations[1].line == 6

    def test_column_is_one(self, rule: MD012, config: MD012Config) -> None:
        """Column should always be 1 for blank line violations."""
        content = "# Heading\n\n\nText\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].column == 1

    def test_maximum_zero(self, rule: MD012) -> None:
        """Maximum of 0 means no blank lines are allowed."""
        config = MD012Config(maximum=0)
        content = "# Heading\n\nText\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 2

    def test_whitespace_only_lines(self, rule: MD012, config: MD012Config) -> None:
        """Lines with only whitespace count as blank."""
        content = "# Heading\n \n   \nText\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3

    def test_front_matter_with_blank_lines(self, rule: MD012, config: MD012Config) -> None:
        """Blank lines inside front matter are excluded."""
        content = "---\nkey: value\n\n\nanother: value\n---\n\n# Heading\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_html_comment_with_blank_lines(self, rule: MD012, config: MD012Config) -> None:
        """Multiple blank lines inside HTML comments trigger violations."""
        content = "# Heading\n\n<!-- comment\n\n\nend -->\n\nText\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 5
