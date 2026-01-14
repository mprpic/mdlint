from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md021 import MD021, MD021Config
from tests.conftest import load_fixture


class TestMD021:
    @pytest.fixture
    def rule(self) -> MD021:
        return MD021()

    @pytest.fixture
    def config(self) -> MD021Config:
        return MD021Config()

    def test_valid_document(self, rule: MD021, config: MD021Config) -> None:
        """Valid document with single space inside hashes passes."""
        content = load_fixture("md021", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD021, config: MD021Config) -> None:
        """Invalid document with multiple spaces triggers violations."""
        content = load_fixture("md021", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 3
        assert violations[0].rule_id == "MD021"
        assert violations[0].line == 1
        assert violations[1].line == 3
        assert violations[2].line == 5

    def test_multiple_left_only(self, rule: MD021, config: MD021Config) -> None:
        """Headings with multiple spaces on left side only."""
        content = load_fixture("md021", "multiple_left_only.md")
        doc = Document(Path("multiple_left_only.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 1
        assert violations[1].line == 3

    def test_multiple_right_only(self, rule: MD021, config: MD021Config) -> None:
        """Headings with multiple spaces on right side only."""
        content = load_fixture("md021", "multiple_right_only.md")
        doc = Document(Path("multiple_right_only.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 1
        assert violations[1].line == 3

    def test_regular_atx_headings(self, rule: MD021, config: MD021Config) -> None:
        """Regular ATX headings without closing hashes should not trigger."""
        content = load_fixture("md021", "regular_atx.md")
        doc = Document(Path("regular_atx.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_no_headings(self, rule: MD021, config: MD021Config) -> None:
        """Document without headings."""
        content = load_fixture("md021", "no_headings.md")
        doc = Document(Path("no_headings.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_message_both_sides(self, rule: MD021, config: MD021Config) -> None:
        """Both sides multiple produces combined message."""
        content = load_fixture("md021", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert violations[0].message == "Multiple spaces inside hashes on closed ATX heading"

    def test_message_left_only(self, rule: MD021, config: MD021Config) -> None:
        """Left side multiple produces left-specific message."""
        content = load_fixture("md021", "multiple_left_only.md")
        doc = Document(Path("multiple_left_only.md"), content)

        violations = rule.check(doc, config)

        assert violations[0].message == "Multiple spaces after opening hashes on closed ATX heading"

    def test_message_right_only(self, rule: MD021, config: MD021Config) -> None:
        """Right side multiple produces right-specific message."""
        content = load_fixture("md021", "multiple_right_only.md")
        doc = Document(Path("multiple_right_only.md"), content)

        violations = rule.check(doc, config)

        assert (
            violations[0].message == "Multiple spaces before closing hashes on closed ATX heading"
        )

    def test_violation_details(self, rule: MD021, config: MD021Config) -> None:
        """Violation includes correct details."""
        content = load_fixture("md021", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert violations[0].rule_id == "MD021"
        assert violations[0].rule_name == "no-multiple-space-closed-atx"
        assert violations[0].column == 1
        assert "#  Heading 1  #" in violations[0].context

    def test_mismatched_hashes(self, rule: MD021, config: MD021Config) -> None:
        """Mismatched opening/closing hash counts should still trigger."""
        content = load_fixture("md021", "mismatched_hashes.md")
        doc = Document(Path("mismatched_hashes.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 1
        assert violations[1].line == 3

    def test_in_code_block(self, rule: MD021, config: MD021Config) -> None:
        """Heading-like content inside code blocks should not trigger."""
        content = "```\n#  Heading  #\n```\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_tab_spacing(self, rule: MD021, config: MD021Config) -> None:
        """Tabs count as spacing and multiple tabs should trigger."""
        content = "#\t\tHeading\t\t#\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
