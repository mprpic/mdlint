from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md005 import MD005, MD005Config
from tests.conftest import load_fixture


class TestMD005:
    @pytest.fixture
    def rule(self) -> MD005:
        return MD005()

    @pytest.fixture
    def config(self) -> MD005Config:
        return MD005Config()

    def test_valid_consistent_indentation(self, rule: MD005, config: MD005Config) -> None:
        """Valid document with consistent indentation."""
        content = load_fixture("md005", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_inconsistent_indentation(self, rule: MD005, config: MD005Config) -> None:
        """Invalid document with inconsistent indentation."""
        content = load_fixture("md005", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD005"
        assert violations[0].line == 5
        assert violations[0].column == 4
        assert "Expected 2 spaces, found 3" in violations[0].message

    def test_no_lists(self, rule: MD005, config: MD005Config) -> None:
        """Document without lists."""
        content = load_fixture("md005", "no_lists.md")
        doc = Document(Path("no_lists.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_flat_list(self, rule: MD005, config: MD005Config) -> None:
        """Flat list with no nesting."""
        content = load_fixture("md005", "flat_list.md")
        doc = Document(Path("flat.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_single_item(self, rule: MD005, config: MD005Config) -> None:
        """Document with single list item."""
        content = load_fixture("md005", "single_item.md")
        doc = Document(Path("single.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_ordered_list_valid(self, rule: MD005, config: MD005Config) -> None:
        """Valid ordered list with consistent indentation."""
        content = load_fixture("md005", "ordered_valid.md")
        doc = Document(Path("ordered_valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_ordered_list_invalid(self, rule: MD005, config: MD005Config) -> None:
        """Invalid ordered list with inconsistent indentation."""
        content = load_fixture("md005", "ordered_invalid.md")
        doc = Document(Path("ordered_invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD005"
        assert violations[0].line == 5
        assert violations[0].column == 5
        assert "Expected 3 spaces, found 4" in violations[0].message

    def test_right_aligned_ordered_valid(self, rule: MD005, config: MD005Config) -> None:
        """Right-aligned ordered list markers should not trigger violations."""
        content = load_fixture("md005", "right_aligned_valid.md")
        doc = Document(Path("right_aligned_valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_right_aligned_ordered_invalid(self, rule: MD005, config: MD005Config) -> None:
        """Inconsistent right-aligned ordered list markers should trigger violations."""
        content = load_fixture("md005", "right_aligned_invalid.md")
        doc = Document(Path("right_aligned_invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD005"
        assert violations[0].line == 4
        assert violations[0].column == 3
        assert "Expected marker end at column 3, found column 5" in violations[0].message

    def test_mixed_nesting(self, rule: MD005, config: MD005Config) -> None:
        """Mixed ordered/unordered nesting should not produce false positives."""
        content = load_fixture("md005", "mixed_nesting.md")
        doc = Document(Path("mixed_nesting.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_lists(self, rule: MD005, config: MD005Config) -> None:
        """Multiple independent lists in a document should be checked separately."""
        content = load_fixture("md005", "multiple_lists.md")
        doc = Document(Path("multiple_lists.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_empty_document(self, rule: MD005, config: MD005Config) -> None:
        """Empty document should produce no violations."""
        content = load_fixture("md005", "empty.md")
        doc = Document(Path("empty.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0


class TestMD005Fix:
    @pytest.fixture
    def rule(self) -> MD005:
        return MD005()

    @pytest.fixture
    def config(self) -> MD005Config:
        return MD005Config()

    def test_fix_corrects_invalid(self, rule: MD005, config: MD005Config) -> None:
        """Fix adjusts indentation to be consistent."""
        content = load_fixture("md005", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_returns_none_for_valid(self, rule: MD005, config: MD005Config) -> None:
        """Fix returns None when there are no violations."""
        content = load_fixture("md005", "valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_ordered_list_invalid(self, rule: MD005, config: MD005Config) -> None:
        """Fix adjusts ordered list indentation to be consistent."""
        content = load_fixture("md005", "ordered_invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_ordered_valid(self, rule: MD005, config: MD005Config) -> None:
        """Fix returns None for valid ordered list."""
        content = load_fixture("md005", "ordered_valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_right_aligned_invalid(self, rule: MD005, config: MD005Config) -> None:
        """Fix adjusts right-aligned ordered list markers."""
        content = load_fixture("md005", "right_aligned_invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_right_aligned_valid(self, rule: MD005, config: MD005Config) -> None:
        """Fix returns None for valid right-aligned ordered list."""
        content = load_fixture("md005", "right_aligned_valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_no_lists(self, rule: MD005, config: MD005Config) -> None:
        """Fix returns None for document without lists."""
        content = load_fixture("md005", "no_lists.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_multiple_lists(self, rule: MD005, config: MD005Config) -> None:
        """Fix returns None for valid multiple independent lists."""
        content = load_fixture("md005", "multiple_lists.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fixable_property(self, rule: MD005) -> None:
        """Rule reports as fixable."""
        assert rule.fixable is True
