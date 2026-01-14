from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md009 import MD009, MD009Config
from tests.conftest import load_fixture


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

    def test_code_blocks_checked_by_default(self, rule: MD009, config: MD009Config) -> None:
        """Code blocks are checked for trailing spaces by default."""
        content = load_fixture("md009", "code_block.md")
        doc = Document(Path("code_block.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD009"

    def test_code_blocks_ignored_when_configured(self, rule: MD009) -> None:
        """Code blocks are ignored when code_blocks=False."""
        config = MD009Config(code_blocks=False)
        content = load_fixture("md009", "code_block.md")
        doc = Document(Path("code_block.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_indented_code_block_ignored(self, rule: MD009) -> None:
        """Indented code blocks are ignored when code_blocks=False."""
        config = MD009Config(code_blocks=False)
        content = "# Heading\n\n    code with trailing spaces   \n\nEnd.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_indented_code_block_checked_by_default(self, rule: MD009, config: MD009Config) -> None:
        """Indented code blocks are checked by default."""
        content = "# Heading\n\n    code with trailing spaces   \n\nEnd.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
