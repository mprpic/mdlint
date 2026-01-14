from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md029 import MD029, MD029Config
from tests.conftest import load_fixture


class TestMD029:
    @pytest.fixture
    def rule(self) -> MD029:
        return MD029()

    def test_valid_one_style(self, rule: MD029) -> None:
        """Valid document with all '1.' prefixes using one style."""
        config = MD029Config(style="one")
        content = load_fixture("md029", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_inconsistent_prefixes(self, rule: MD029) -> None:
        """Invalid document with inconsistent prefixes using one style."""
        config = MD029Config(style="one")
        content = load_fixture("md029", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD029"
        assert violations[0].line == 4
        assert "expected 1, found 3" in violations[0].message
        assert violations[1].line == 5
        assert "expected 1, found 2" in violations[1].message

    def test_no_lists(self, rule: MD029) -> None:
        """Document without lists."""
        config = MD029Config(style="one")
        content = load_fixture("md029", "no_lists.md")
        doc = Document(Path("no_lists.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_ordered_style_valid(self, rule: MD029) -> None:
        """Valid sequential numbering with ordered style."""
        config = MD029Config(style="ordered")
        content = load_fixture("md029", "ordered_valid.md")
        doc = Document(Path("ordered_valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_ordered_style_invalid(self, rule: MD029) -> None:
        """Invalid prefixes with ordered style (all 1s)."""
        config = MD029Config(style="ordered")
        content = load_fixture("md029", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert "expected 2" in violations[0].message
        assert "expected 3" in violations[1].message

    def test_ordered_style_zero_start_valid(self, rule: MD029) -> None:
        """Valid 0-starting sequential list with ordered style."""
        config = MD029Config(style="ordered")
        content = load_fixture("md029", "ordered_zero_start.md")
        doc = Document(Path("ordered_zero_start.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_ordered_style_zero_start_invalid(self, rule: MD029) -> None:
        """Zero-repeat list is invalid with ordered style (expects 0/1/2)."""
        config = MD029Config(style="ordered")
        content = load_fixture("md029", "zero_repeat.md")
        doc = Document(Path("zero_repeat.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert "expected 1, found 0" in violations[0].message
        assert "expected 2, found 0" in violations[1].message

    def test_one_style_invalid_ordered(self, rule: MD029) -> None:
        """Invalid sequential numbering with one style."""
        config = MD029Config(style="one")
        content = load_fixture("md029", "ordered_valid.md")
        doc = Document(Path("ordered_valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert "expected 1" in violations[0].message

    def test_zero_style_valid(self, rule: MD029) -> None:
        """Valid zero prefixes with zero style."""
        config = MD029Config(style="zero")
        content = load_fixture("md029", "zero_valid.md")
        doc = Document(Path("zero_valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_one_or_ordered_accepts_one(self, rule: MD029) -> None:
        """one_or_ordered style accepts all 1s."""
        config = MD029Config(style="one_or_ordered")
        content = load_fixture("md029", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_one_or_ordered_accepts_ordered(self, rule: MD029) -> None:
        """one_or_ordered style accepts sequential numbering."""
        config = MD029Config(style="one_or_ordered")
        content = load_fixture("md029", "ordered_valid.md")
        doc = Document(Path("ordered_valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_one_or_ordered_accepts_zero_start_ordered(self, rule: MD029) -> None:
        """one_or_ordered style accepts 0-starting sequential numbering."""
        config = MD029Config(style="one_or_ordered")
        content = load_fixture("md029", "ordered_zero_start.md")
        doc = Document(Path("ordered_zero_start.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_one_or_ordered_rejects_inconsistent(self, rule: MD029) -> None:
        """one_or_ordered style rejects inconsistent numbering (1/3/2)."""
        config = MD029Config(style="one_or_ordered")
        content = load_fixture("md029", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        # Detected as ordered (second item 3 != 1), expects 1/2/3
        assert len(violations) == 2
        assert violations[0].line == 4
        assert "expected 2, found 3" in violations[0].message
        assert violations[1].line == 5
        assert "expected 3, found 2" in violations[1].message

    def test_one_or_ordered_rejects_zero_repeat(self, rule: MD029) -> None:
        """one_or_ordered rejects 0/0/0 (detected as ordered, expects 0/1/2)."""
        config = MD029Config(style="one_or_ordered")
        content = load_fixture("md029", "zero_repeat.md")
        doc = Document(Path("zero_repeat.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 4
        assert "expected 1, found 0" in violations[0].message
        assert violations[1].line == 5
        assert "expected 2, found 0" in violations[1].message

    def test_one_or_ordered_rejects_arbitrary_start(self, rule: MD029) -> None:
        """one_or_ordered rejects lists starting with numbers > 1."""
        config = MD029Config(style="one_or_ordered")
        content = load_fixture("md029", "arbitrary_start.md")
        doc = Document(Path("arbitrary_start.md"), content)

        violations = rule.check(doc, config)

        # Detected as ordered (second item 6 != 1), expects 1/2/3
        assert len(violations) == 3
        assert "expected 1, found 5" in violations[0].message
        assert "expected 2, found 6" in violations[1].message
        assert "expected 3, found 7" in violations[2].message

    def test_nested_lists(self, rule: MD029) -> None:
        """Nested lists with consistent prefixes."""
        config = MD029Config(style="one")
        content = load_fixture("md029", "nested.md")
        doc = Document(Path("nested.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_single_item_list(self, rule: MD029) -> None:
        """Single-item lists are valid with one_or_ordered."""
        config = MD029Config(style="one_or_ordered")
        content = load_fixture("md029", "single_item.md")
        doc = Document(Path("single_item.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_single_item_list_invalid(self, rule: MD029) -> None:
        """Single-item list with prefix > 1 is invalid with one_or_ordered."""
        config = MD029Config(style="one_or_ordered")
        content = load_fixture("md029", "single_item_invalid.md")
        doc = Document(Path("single_item_invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "expected 1, found 5" in violations[0].message

    def test_multiple_separate_lists(self, rule: MD029) -> None:
        """Multiple separate lists are each validated independently."""
        config = MD029Config(style="one")
        content = load_fixture("md029", "multiple_lists.md")
        doc = Document(Path("multiple_lists.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_default_style_is_one_or_ordered(self) -> None:
        """Default config uses one_or_ordered style."""
        config = MD029Config()

        assert config.style == "one_or_ordered"
