from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md020 import MD020, MD020Config
from tests.conftest import load_fixture


class TestMD020:
    @pytest.fixture
    def rule(self) -> MD020:
        return MD020()

    @pytest.fixture
    def config(self) -> MD020Config:
        return MD020Config()

    def test_valid_document(self, rule: MD020, config: MD020Config) -> None:
        """Valid document with proper spacing passes the rule."""
        content = load_fixture("md020", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD020, config: MD020Config) -> None:
        """Invalid document with missing spaces triggers violations."""
        content = load_fixture("md020", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 3
        assert violations[0].rule_id == "MD020"
        assert violations[0].line == 1
        assert violations[1].line == 3
        assert violations[2].line == 5

    def test_missing_left_space(self, rule: MD020, config: MD020Config) -> None:
        """Headings missing space on left side only."""
        content = load_fixture("md020", "missing_left_space.md")
        doc = Document(Path("missing_left_space.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 1
        assert violations[1].line == 3

    def test_missing_right_space(self, rule: MD020, config: MD020Config) -> None:
        """Headings missing space on right side only."""
        content = load_fixture("md020", "missing_right_space.md")
        doc = Document(Path("missing_right_space.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 1
        assert violations[1].line == 3

    def test_regular_atx_headings(self, rule: MD020, config: MD020Config) -> None:
        """Regular ATX headings without closing hashes should not trigger."""
        content = load_fixture("md020", "regular_atx.md")
        doc = Document(Path("regular_atx.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_no_headings(self, rule: MD020, config: MD020Config) -> None:
        """Document without headings."""
        content = load_fixture("md020", "no_headings.md")
        doc = Document(Path("no_headings.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_message_both_sides(self, rule: MD020, config: MD020Config) -> None:
        """Both sides missing produces combined message."""
        content = load_fixture("md020", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert violations[0].message == "No space inside hashes on closed ATX heading"

    def test_message_left_only(self, rule: MD020, config: MD020Config) -> None:
        """Left side missing produces left-specific message."""
        content = load_fixture("md020", "missing_left_space.md")
        doc = Document(Path("missing_left_space.md"), content)

        violations = rule.check(doc, config)

        assert violations[0].message == "No space after opening hashes on closed ATX heading"

    def test_message_right_only(self, rule: MD020, config: MD020Config) -> None:
        """Right side missing produces right-specific message."""
        content = load_fixture("md020", "missing_right_space.md")
        doc = Document(Path("missing_right_space.md"), content)

        violations = rule.check(doc, config)

        assert violations[0].message == "No space before closing hashes on closed ATX heading"

    def test_column_is_one(self, rule: MD020, config: MD020Config) -> None:
        """Column should always be 1."""
        content = load_fixture("md020", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        for v in violations:
            assert v.column == 1

    def test_context_contains_line(self, rule: MD020, config: MD020Config) -> None:
        """Context should contain the raw line content."""
        content = load_fixture("md020", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert violations[0].context == "#Heading 1#"
        assert violations[1].context == "##Heading 2##"

    def test_in_code_block(self, rule: MD020, config: MD020Config) -> None:
        """Heading-like content inside code blocks should be ignored."""
        content = load_fixture("md020", "in_code_block.md")
        doc = Document(Path("in_code_block.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_in_html_block(self, rule: MD020, config: MD020Config) -> None:
        """Heading-like content inside HTML blocks should be ignored."""
        content = "<div>\n#Heading#\n</div>\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_escaped_hash(self, rule: MD020, config: MD020Config) -> None:
        """Escaped hash at end of line should not trigger."""
        content = load_fixture("md020", "escaped_hash.md")
        doc = Document(Path("escaped_hash.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_mismatched_hashes(self, rule: MD020, config: MD020Config) -> None:
        """Mismatched opening/closing hash counts should still trigger."""
        content = load_fixture("md020", "mismatched_hashes.md")
        doc = Document(Path("mismatched_hashes.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 1
        assert violations[1].line == 3

    def test_single_char_heading(self, rule: MD020, config: MD020Config) -> None:
        """Single character heading should trigger."""
        content = "#a#\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1

    def test_trailing_whitespace(self, rule: MD020, config: MD020Config) -> None:
        """Trailing whitespace after closing hashes should still trigger."""
        content = "#Heading#   \n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_fix_corrects_invalid(self, rule: MD020, config: MD020Config) -> None:
        """Fix inserts spaces inside hashes in invalid headings."""
        content = load_fixture("md020", "invalid.md")
        doc = Document(Path("invalid.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert "# Heading 1 #" in result
        assert "## Heading 2 ##" in result
        assert "### Heading 3 ###" in result
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_returns_none_for_valid(self, rule: MD020, config: MD020Config) -> None:
        """Fix returns None when content is already valid."""
        content = load_fixture("md020", "valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_missing_left_space(self, rule: MD020, config: MD020Config) -> None:
        """Fix inserts space on left side only."""
        content = load_fixture("md020", "missing_left_space.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert "# Heading 1 #" in result
        assert "## Heading 2 ##" in result
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_missing_right_space(self, rule: MD020, config: MD020Config) -> None:
        """Fix inserts space on right side only."""
        content = load_fixture("md020", "missing_right_space.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert "# Heading 1 #" in result
        assert "## Heading 2 ##" in result
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_ignores_code_blocks(self, rule: MD020, config: MD020Config) -> None:
        """Fix does not modify lines inside code blocks."""
        content = load_fixture("md020", "in_code_block.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_ignores_html_blocks(self, rule: MD020, config: MD020Config) -> None:
        """Fix does not modify lines inside HTML blocks."""
        content = "<div>\n#Heading#\n</div>\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_mismatched_hashes(self, rule: MD020, config: MD020Config) -> None:
        """Fix handles mismatched opening/closing hash counts."""
        content = load_fixture("md020", "mismatched_hashes.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert "# Heading ##" in result
        assert "## Heading #" in result
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_single_char_heading(self, rule: MD020, config: MD020Config) -> None:
        """Fix handles single character heading."""
        content = "#a#\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert result == "# a #\n"
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_trailing_whitespace(self, rule: MD020, config: MD020Config) -> None:
        """Fix handles headings with trailing whitespace after closing hashes."""
        content = "#Heading#   \n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert "# Heading #" in result
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []
