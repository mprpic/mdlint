from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md031 import MD031, MD031Config
from tests.conftest import load_fixture


class TestMD031:
    @pytest.fixture
    def rule(self) -> MD031:
        return MD031()

    @pytest.fixture
    def config(self) -> MD031Config:
        return MD031Config()

    def test_valid_document(self, rule: MD031, config: MD031Config) -> None:
        """Valid document passes the rule."""
        content = load_fixture("md031", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD031, config: MD031Config) -> None:
        """Invalid document triggers violations for missing blanks above and below."""
        content = load_fixture("md031", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD031"
        assert violations[0].line == 2
        assert violations[0].column == 1
        assert "preceded" in violations[0].message.lower()
        assert "```" in violations[0].context
        assert violations[1].line == 5
        assert violations[1].column == 1
        assert "followed" in violations[1].message.lower()
        assert "```" in violations[1].context

    def test_no_blank_line_above(self, rule: MD031, config: MD031Config) -> None:
        """Code fence without blank line above triggers violation."""
        content = load_fixture("md031", "no_blank_above.md")
        doc = Document(Path("no_blank_above.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 2
        assert "preceded" in violations[0].message.lower()

    def test_no_blank_line_below(self, rule: MD031, config: MD031Config) -> None:
        """Code fence without blank line below triggers violation."""
        content = load_fixture("md031", "no_blank_below.md")
        doc = Document(Path("no_blank_below.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 5
        assert "followed" in violations[0].message.lower()

    def test_fence_at_document_boundaries(self, rule: MD031, config: MD031Config) -> None:
        """Code fences at start and end of document don't need surrounding blank lines."""
        content = load_fixture("md031", "boundaries.md")
        doc = Document(Path("boundaries.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_fences_valid(self, rule: MD031, config: MD031Config) -> None:
        """Multiple code fences all properly spaced."""
        content = load_fixture("md031", "multiple_valid.md")
        doc = Document(Path("multiple_valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_fences_invalid(self, rule: MD031, config: MD031Config) -> None:
        """Multiple code fences with missing blank lines."""
        content = load_fixture("md031", "multiple_invalid.md")
        doc = Document(Path("multiple_invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 4

    def test_tilde_fence(self, rule: MD031, config: MD031Config) -> None:
        """Tilde-style code fences are also checked."""
        content = load_fixture("md031", "tilde_fence.md")
        doc = Document(Path("tilde_fence.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2

    def test_list_items_default(self, rule: MD031, config: MD031Config) -> None:
        """By default, code fences in list items are checked."""
        content = load_fixture("md031", "list_items.md")
        doc = Document(Path("list_items.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 2
        assert "preceded" in violations[0].message.lower()
        assert violations[1].line == 4
        assert "followed" in violations[1].message.lower()

    def test_list_items_disabled(self, rule: MD031) -> None:
        """With list_items=False, code fences in list items are not checked."""
        config = MD031Config(list_items=False)
        content = load_fixture("md031", "list_items.md")
        doc = Document(Path("list_items.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_list_items_disabled_non_list_fences(self, rule: MD031) -> None:
        """With list_items=False, fences outside lists are still checked."""
        config = MD031Config(list_items=False)
        content = load_fixture("md031", "no_blank_above.md")
        doc = Document(Path("no_blank_above.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_indented_fence_in_list(self, rule: MD031, config: MD031Config) -> None:
        """Properly spaced code fence in list item passes."""
        content = load_fixture("md031", "list_items_spaced.md")
        doc = Document(Path("list_items_spaced.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_consecutive_fences(self, rule: MD031, config: MD031Config) -> None:
        """Two consecutive fences with no blank line between them."""
        content = load_fixture("md031", "consecutive_fences.md")
        doc = Document(Path("consecutive_fences.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 3
        assert "followed" in violations[0].message.lower()
        assert violations[1].line == 4
        assert "preceded" in violations[1].message.lower()

    def test_fence_after_heading(self, rule: MD031, config: MD031Config) -> None:
        """Code fence directly after a heading triggers violation."""
        content = load_fixture("md031", "fence_after_heading.md")
        doc = Document(Path("fence_after_heading.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 2
        assert "preceded" in violations[0].message.lower()

    def test_empty_fence(self, rule: MD031, config: MD031Config) -> None:
        """Empty code fence without surrounding blank lines."""
        content = load_fixture("md031", "empty_fence.md")
        doc = Document(Path("empty_fence.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert "preceded" in violations[0].message.lower()
        assert "followed" in violations[1].message.lower()

    def test_unclosed_fence(self, rule: MD031, config: MD031Config) -> None:
        """Unclosed fence does not crash and produces no violation at end."""
        content = load_fixture("md031", "unclosed_fence.md")
        doc = Document(Path("unclosed_fence.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_fix_returns_none_for_valid(self, rule: MD031, config: MD031Config) -> None:
        """Fixing already valid content returns None."""
        content = load_fixture("md031", "valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_corrects_invalid(self, rule: MD031, config: MD031Config) -> None:
        """Fixing invalid content adds blank lines above and below fences."""
        content = load_fixture("md031", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_no_blank_above(self, rule: MD031, config: MD031Config) -> None:
        """Fixing adds blank line above fence."""
        content = load_fixture("md031", "no_blank_above.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_no_blank_below(self, rule: MD031, config: MD031Config) -> None:
        """Fixing adds blank line below fence."""
        content = load_fixture("md031", "no_blank_below.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_multiple_fences(self, rule: MD031, config: MD031Config) -> None:
        """Fixing multiple invalid fences adds blank lines around all of them."""
        content = load_fixture("md031", "multiple_invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_consecutive_fences(self, rule: MD031, config: MD031Config) -> None:
        """Fixing consecutive fences adds blank line between them."""
        content = load_fixture("md031", "consecutive_fences.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_tilde_fence(self, rule: MD031, config: MD031Config) -> None:
        """Fixing tilde-style fences works correctly."""
        content = load_fixture("md031", "tilde_fence.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_empty_fence(self, rule: MD031, config: MD031Config) -> None:
        """Fixing empty fence adds blank lines around it."""
        content = load_fixture("md031", "empty_fence.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_fence_after_heading(self, rule: MD031, config: MD031Config) -> None:
        """Fixing adds blank line between heading and fence."""
        content = load_fixture("md031", "fence_after_heading.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_boundaries(self, rule: MD031, config: MD031Config) -> None:
        """Fences at document boundaries need no fix."""
        content = load_fixture("md031", "boundaries.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_multiple_valid(self, rule: MD031, config: MD031Config) -> None:
        """Multiple valid fences need no fix."""
        content = load_fixture("md031", "multiple_valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_list_items_default(self, rule: MD031, config: MD031Config) -> None:
        """Fixing list items with default config adds blank lines."""
        content = load_fixture("md031", "list_items.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_list_items_disabled(self, rule: MD031) -> None:
        """With list_items=False, fences in lists are not fixed."""
        config = MD031Config(list_items=False)
        content = load_fixture("md031", "list_items.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_list_items_spaced(self, rule: MD031, config: MD031Config) -> None:
        """Already spaced list items need no fix."""
        content = load_fixture("md031", "list_items_spaced.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None
