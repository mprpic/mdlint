from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md009 import MD009, MD009Config
from tests.conftest import load_fixture


def _fix_twice(rule: MD009, config: MD009Config, content: str) -> str:
    """Apply the fix and check that a second pass changes nothing."""
    result = rule.fix(Document(Path("test.md"), content), config)
    assert result is not None
    assert rule.fix(Document(Path("test.md"), result), config) is None
    return result


class TestMD009:
    @pytest.fixture
    def rule(self) -> MD009:
        return MD009()

    @pytest.fixture
    def config(self) -> MD009Config:
        return MD009Config()

    def test_valid_document(self, rule: MD009, config: MD009Config) -> None:
        """Valid document passes the rule."""
        content = load_fixture("md009", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD009, config: MD009Config) -> None:
        """Invalid document triggers violations."""
        content = load_fixture("md009", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD009"
        assert violations[0].line == 3
        assert "trailing whitespace" in violations[0].message.lower()

    def test_hard_break_allowed(self, rule: MD009, config: MD009Config) -> None:
        """Hard break with exactly br_spaces trailing spaces is allowed."""
        content = load_fixture("md009", "hard_break_valid.md")
        doc = Document(Path("hard_break_valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_single_trailing_space(self, rule: MD009, config: MD009Config) -> None:
        """Single trailing space triggers violation."""
        content = "# Heading\n\nLine with one trailing space. \n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3
        assert violations[0].rule_id == "MD009"

    def test_br_spaces_zero_disables_exception(self, rule: MD009) -> None:
        """Setting br_spaces to 0 disallows all trailing spaces."""
        config = MD009Config(br_spaces=0)
        content = "# Heading\n\nLine with hard break.  \n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_br_spaces_one_disables_exception(self, rule: MD009) -> None:
        """Setting br_spaces to 1 also disallows trailing spaces."""
        config = MD009Config(br_spaces=1)
        content = "# Heading\n\nLine with two spaces.  \n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_trailing_spaces_not_matching_br_spaces(self, rule: MD009, config: MD009Config) -> None:
        """Trailing spaces not matching br_spaces trigger violation."""
        # Default br_spaces is 2, so 3 spaces should trigger violation
        content = "# Heading\n\nLine with three spaces.   \n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3

    def test_empty_line_with_spaces(self, rule: MD009, config: MD009Config) -> None:
        """Empty line with only spaces triggers violation."""
        content = "# Heading\n   \nParagraph.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 2

    def test_multiple_violations(self, rule: MD009, config: MD009Config) -> None:
        """Multiple lines with trailing spaces."""
        content = "Line 1 \nLine 2  \nLine 3   \n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        # Line 1 has 1 space (violation), Line 2 has 2 spaces (allowed),
        # Line 3 has 3 spaces (violation)
        assert len(violations) == 2
        assert violations[0].line == 1
        assert violations[1].line == 3

    def test_column_points_to_first_trailing_space(self, rule: MD009, config: MD009Config) -> None:
        """Column should point to the first trailing space."""
        content = "Hello   \n"  # "Hello" is 5 chars, spaces start at column 6
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].column == 6

    def test_no_trailing_newline(self, rule: MD009, config: MD009Config) -> None:
        """File without trailing newline."""
        content = "# Heading\n\nNo trailing newline"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_trailing_tab(self, rule: MD009, config: MD009Config) -> None:
        """Trailing tab character triggers violation."""
        content = "Line with tab\t\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert violations[0].column == 14
        assert "trailing whitespace" in violations[0].message.lower()

    def test_br_spaces_custom_value(self, rule: MD009) -> None:
        """Custom br_spaces value allows that many trailing spaces."""
        config = MD009Config(br_spaces=4)
        content = "Text with four spaces.    \n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_br_spaces_custom_value_mismatch(self, rule: MD009) -> None:
        """Trailing spaces not matching custom br_spaces trigger violation."""
        config = MD009Config(br_spaces=4)
        content = "Text with two spaces.  \n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_blank_line_with_br_spaces_still_flagged(
        self, rule: MD009, config: MD009Config
    ) -> None:
        """Blank line with exactly br_spaces spaces is still flagged."""
        # A blank line can't produce a <br>, so it should be flagged
        content = "# Heading\n  \nParagraph.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 2

    def test_code_blocks_ignored_by_default(self, rule: MD009, config: MD009Config) -> None:
        """Code blocks are ignored by default."""
        content = load_fixture("md009", "code_block.md")
        doc = Document(Path("code_block.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_code_blocks_checked_when_configured(self, rule: MD009) -> None:
        """Code blocks are checked when code_blocks=True."""
        config = MD009Config(code_blocks=True)
        content = load_fixture("md009", "code_block.md")
        doc = Document(Path("code_block.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD009"

    def test_indented_code_block_ignored_by_default(self, rule: MD009, config: MD009Config) -> None:
        """Indented code blocks are ignored by default."""
        content = "# Heading\n\n    code with trailing spaces   \n\nEnd.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_indented_code_block_checked_when_configured(self, rule: MD009) -> None:
        """Indented code blocks are checked when code_blocks=True."""
        config = MD009Config(code_blocks=True)
        content = "# Heading\n\n    code with trailing spaces   \n\nEnd.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_multiline_code_span_ignored_by_default(self, rule: MD009, config: MD009Config) -> None:
        """Trailing whitespace inside a multi-line code span is code content."""
        content = load_fixture("md009", "code_span_multiline.md")
        doc = Document(Path("code_span_multiline.md"), content)

        violations = rule.check(doc, config)

        assert [v.line for v in violations] == [6]

    def test_multiline_code_span_checked_when_configured(self, rule: MD009) -> None:
        """Code spans are checked when code_blocks=True."""
        config = MD009Config(code_blocks=True)
        content = load_fixture("md009", "code_span_multiline.md")
        doc = Document(Path("code_span_multiline.md"), content)

        violations = rule.check(doc, config)

        assert [v.line for v in violations] == [3, 6]

    def test_front_matter_ignored(self, rule: MD009) -> None:
        """Front matter is never checked, whatever code_blocks is set to."""
        content = load_fixture("md009", "front_matter.md")
        doc = Document(Path("front_matter.md"), content)

        assert rule.check(doc, MD009Config()) == []
        assert rule.check(doc, MD009Config(code_blocks=True)) == []


class TestMD009Fix:
    @pytest.fixture
    def rule(self) -> MD009:
        return MD009()

    @pytest.fixture
    def config(self) -> MD009Config:
        return MD009Config()

    def test_fix_corrects_invalid(self, rule: MD009, config: MD009Config) -> None:
        """Fix removes trailing spaces from invalid document."""
        content = load_fixture("md009", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_returns_none_for_valid(self, rule: MD009, config: MD009Config) -> None:
        """Fix returns None when there are no violations."""
        content = load_fixture("md009", "valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_preserves_hard_breaks(self, rule: MD009, config: MD009Config) -> None:
        """Fix preserves valid hard break trailing spaces."""
        content = load_fixture("md009", "hard_break_valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_multiple_violations(self, rule: MD009, config: MD009Config) -> None:
        """Fix removes trailing spaces from multiple lines."""
        content = "Line 1 \nLine 2  \nLine 3   \n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        # Line 2 has exactly 2 spaces (valid hard break), should be preserved
        assert result == "Line 1\nLine 2  \nLine 3\n"

    def test_fix_empty_line_with_spaces(self, rule: MD009, config: MD009Config) -> None:
        """Fix removes spaces from blank lines."""
        content = "# Heading\n   \nParagraph.\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert result == "# Heading\n\nParagraph.\n"

    def test_fix_trailing_tab(self, rule: MD009, config: MD009Config) -> None:
        """Fix removes trailing tab characters."""
        content = "Line with tab\t\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert result == "Line with tab\n"

    def test_fix_code_blocks_when_configured(self, rule: MD009) -> None:
        """Fix removes trailing spaces in code blocks when code_blocks=True."""
        config = MD009Config(code_blocks=True)
        content = load_fixture("md009", "code_block.md")
        result = _fix_twice(rule, config, content)
        assert "x = 1\n" in result

    def test_fix_skips_code_blocks_by_default(self, rule: MD009, config: MD009Config) -> None:
        """Fix leaves code blocks alone by default."""
        content = load_fixture("md009", "code_block.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_keeps_multiline_code_span_content(self, rule: MD009, config: MD009Config) -> None:
        """Fix leaves whitespace inside a multi-line code span untouched by default."""
        content = load_fixture("md009", "code_span_multiline.md")
        result = _fix_twice(rule, config, content)
        assert result == content.replace("span.   \n", "span.\n")

    def test_fix_multiline_code_span_when_configured(self, rule: MD009) -> None:
        """Fix strips code span whitespace when code_blocks=True."""
        config = MD009Config(code_blocks=True)
        content = load_fixture("md009", "code_span_multiline.md")
        result = _fix_twice(rule, config, content)
        assert result == content.replace("make   \n", "make\n").replace("span.   \n", "span.\n")

    def test_fix_skips_front_matter(self, rule: MD009, config: MD009Config) -> None:
        """Fix never rewrites front matter."""
        content = load_fixture("md009", "front_matter.md")
        doc = Document(Path("test.md"), content)
        assert rule.fix(doc, config) is None

    def test_fix_br_spaces_zero(self, rule: MD009) -> None:
        """Fix removes all trailing spaces when br_spaces=0."""
        config = MD009Config(br_spaces=0)
        content = "Line with hard break.  \n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert result == "Line with hard break.\n"

    def test_fixable_property(self, rule: MD009) -> None:
        """Rule reports as fixable."""
        assert rule.fixable is True
