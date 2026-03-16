from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md032 import MD032, MD032Config
from tests.conftest import load_fixture


class TestMD032:
    @pytest.fixture
    def rule(self) -> MD032:
        return MD032()

    @pytest.fixture
    def config(self) -> MD032Config:
        return MD032Config()

    def test_valid_document(self, rule: MD032, config: MD032Config) -> None:
        """Valid document passes the rule."""
        content = load_fixture("md032", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD032, config: MD032Config) -> None:
        """Invalid document triggers violations."""
        content = load_fixture("md032", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD032"
        # First list missing blank line above
        assert violations[0].line == 2
        assert "above" in violations[0].message.lower()
        # Second list missing blank line below (reported on last line of list)
        assert violations[1].line == 8
        assert "below" in violations[1].message.lower()

    def test_no_blank_line_above(self, rule: MD032, config: MD032Config) -> None:
        """List without blank line above triggers violation."""
        content = "Some text.\n* Item 1\n* Item 2\n\nMore text.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 2
        assert violations[0].column == 1
        assert "above" in violations[0].message.lower()

    def test_first_list_at_start(self, rule: MD032, config: MD032Config) -> None:
        """First list at start of document doesn't need blank line above."""
        content = "* Item 1\n* Item 2\n\nSome text.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_last_list_at_end(self, rule: MD032, config: MD032Config) -> None:
        """Last list at end of document doesn't need blank line below."""
        content = "Some text.\n\n* Item 1\n* Item 2\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_lists_properly_spaced(self, rule: MD032, config: MD032Config) -> None:
        """Multiple lists all properly spaced."""
        content = "Text.\n\n* Item 1\n* Item 2\n\n1. First\n2. Second\n\nMore text.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_nested_list_no_violations(self, rule: MD032, config: MD032Config) -> None:
        """Nested lists should not trigger violations for inner items."""
        content = "Text.\n\n* Item 1\n  * Nested 1\n  * Nested 2\n* Item 2\n\nMore text.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_lazy_continuation_not_violation(self, rule: MD032, config: MD032Config) -> None:
        """Lazy continuation lines are part of the list, not a violation."""
        content = "Text.\n\n1. List item\n   More item 1\n2. List item\nMore item 2\n\nText.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_list_followed_by_thematic_break(self, rule: MD032, config: MD032Config) -> None:
        """List followed by thematic break without blank line triggers violation."""
        content = "Text.\n\n* Item 1\n* Item 2\n---\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 4
        assert "below" in violations[0].message.lower()

    def test_mixed_markers_no_blanks_around_violations(
        self, rule: MD032, config: MD032Config
    ) -> None:
        """Mixed-marker list parsed as consecutive lists should not trigger."""
        content = load_fixture("md032", "valid_mixed_markers.md")
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_mixed_markers_missing_blank_above(self, rule: MD032, config: MD032Config) -> None:
        """Mixed-marker list without blank line above triggers one violation."""
        content = load_fixture("md032", "invalid_mixed_markers.md")
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 2
        assert "above" in violations[0].message.lower()

    def test_list_in_code_block_no_violations(self, rule: MD032, config: MD032Config) -> None:
        """List-like content inside fenced code block should not trigger."""
        content = "Text.\n\n```\nSome text.\n* Item 1\n* Item 2\nMore text.\n```\n\nText.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0


class TestMD032Fix:
    @pytest.fixture
    def rule(self) -> MD032:
        return MD032()

    @pytest.fixture
    def config(self) -> MD032Config:
        return MD032Config()

    def test_fix_corrects_invalid(self, rule: MD032, config: MD032Config) -> None:
        """Fix inserts blank lines around lists."""
        content = load_fixture("md032", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_returns_none_for_valid(self, rule: MD032, config: MD032Config) -> None:
        """Valid document returns None (nothing to fix)."""
        content = load_fixture("md032", "valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_missing_blank_above(self, rule: MD032, config: MD032Config) -> None:
        """Fix inserts blank line above list."""
        content = "Some text.\n* Item 1\n* Item 2\n\nMore text.\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert result == "Some text.\n\n* Item 1\n* Item 2\n\nMore text.\n"

    def test_fix_missing_blank_below(self, rule: MD032, config: MD032Config) -> None:
        """Fix inserts blank line below list."""
        content = "Text.\n\n* Item 1\n* Item 2\n---\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert result == "Text.\n\n* Item 1\n* Item 2\n\n---\n"

    def test_fix_list_at_start(self, rule: MD032, config: MD032Config) -> None:
        """List at start of document doesn't get blank line added above."""
        content = "* Item 1\n* Item 2\n\nSome text.\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_list_at_end(self, rule: MD032, config: MD032Config) -> None:
        """List at end of document doesn't get blank line added below."""
        content = "Some text.\n\n* Item 1\n* Item 2\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_mixed_markers(self, rule: MD032, config: MD032Config) -> None:
        """Fix handles mixed-marker lists correctly."""
        content = load_fixture("md032", "invalid_mixed_markers.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_multiple_lists_missing_blanks(self, rule: MD032, config: MD032Config) -> None:
        """Fix inserts blank lines for multiple lists."""
        content = "Text.\n* A\n* B\n\n1. One\n2. Two\nMore text.\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []
