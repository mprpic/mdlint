from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md030 import MD030, MD030Config
from tests.conftest import load_fixture


class TestMD030:
    @pytest.fixture
    def rule(self) -> MD030:
        return MD030()

    @pytest.fixture
    def config(self) -> MD030Config:
        return MD030Config()

    def test_valid_document(self, rule: MD030, config: MD030Config) -> None:
        """Valid document with correct single space after list markers."""
        content = load_fixture("md030", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD030, config: MD030Config) -> None:
        """Invalid document with incorrect spacing after list markers."""
        content = load_fixture("md030", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 4
        assert violations[0].rule_id == "MD030"
        assert violations[0].line == 3
        assert violations[0].column == 2
        assert "Expected 1 space" in violations[0].message
        assert "found 2" in violations[0].message
        assert violations[1].line == 4
        assert violations[1].column == 2
        assert "found 3" in violations[1].message
        assert violations[2].line == 6
        assert violations[2].column == 3
        assert violations[3].line == 7
        assert violations[3].column == 3

    def test_no_lists(self, rule: MD030, config: MD030Config) -> None:
        """Document without lists passes."""
        content = load_fixture("md030", "no_lists.md")
        doc = Document(Path("no_lists.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multi_paragraph_list(self, rule: MD030) -> None:
        """Multi-paragraph list with custom spacing."""
        content = load_fixture("md030", "multi_paragraph.md")
        doc = Document(Path("multi_paragraph.md"), content)
        config = MD030Config(ul_multi=3, ol_multi=4)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_custom_ul_single(self, rule: MD030) -> None:
        """Test with custom unordered list single-paragraph spacing."""
        content = load_fixture("md030", "custom_ul_single.md")
        doc = Document(Path("custom_ul_single.md"), content)
        config = MD030Config(ul_single=2)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_custom_ol_single(self, rule: MD030) -> None:
        """Test with custom ordered list single-paragraph spacing."""
        content = load_fixture("md030", "custom_ol_single.md")
        doc = Document(Path("custom_ol_single.md"), content)
        config = MD030Config(ol_single=2)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = MD030Config()

        assert config.ul_single == 1
        assert config.ol_single == 1
        assert config.ul_multi == 1
        assert config.ol_multi == 1

    def test_nested_lists(self, rule: MD030, config: MD030Config) -> None:
        """Test nested lists with correct spacing."""
        content = load_fixture("md030", "nested.md")
        doc = Document(Path("nested.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_mixed_list_types(self, rule: MD030, config: MD030Config) -> None:
        """Test mixed ordered and unordered lists."""
        content = load_fixture("md030", "mixed_list_types.md")
        doc = Document(Path("mixed_list_types.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_nested_list_multi_paragraph_detection(self, rule: MD030) -> None:
        """Outer list with multi-paragraph items retains status across nested lists."""
        content = load_fixture("md030", "nested_multi_paragraph_valid.md")
        doc = Document(Path("nested_multi_paragraph_valid.md"), content)
        config = MD030Config(ul_multi=3)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_nested_list_multi_paragraph_violation(self, rule: MD030) -> None:
        """Outer multi-paragraph list reports violations even with nested lists."""
        content = load_fixture("md030", "nested_multi_paragraph_invalid.md")
        doc = Document(Path("nested_multi_paragraph_invalid.md"), content)
        config = MD030Config(ul_multi=3)

        violations = rule.check(doc, config)

        # Outer list items should expect 3 spaces (multi), but have 1
        assert len(violations) == 2
        assert violations[0].line == 1
        assert violations[1].line == 5

    def test_star_marker(self, rule: MD030, config: MD030Config) -> None:
        """Test * unordered list marker."""
        content = load_fixture("md030", "star_marker.md")
        doc = Document(Path("star_marker.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].column == 2
        assert "found 2" in violations[0].message

    def test_plus_marker(self, rule: MD030, config: MD030Config) -> None:
        """Test + unordered list marker."""
        content = load_fixture("md030", "plus_marker.md")
        doc = Document(Path("plus_marker.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].column == 2
        assert "found 2" in violations[0].message

    def test_multi_digit_ordered_marker(self, rule: MD030, config: MD030Config) -> None:
        """Test multi-digit ordered list markers report correct column."""
        content = load_fixture("md030", "multi_digit_ordered.md")
        doc = Document(Path("multi_digit_ordered.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].column == 4
        assert violations[1].column == 4

    def test_sublist_triggers_multi_paragraph(self, rule: MD030) -> None:
        """A sub-list counts as a block element, making the parent list multi-paragraph."""
        content = load_fixture("md030", "sublist_multi_paragraph.md")
        doc = Document(Path("sublist_multi_paragraph.md"), content)
        config = MD030Config(ul_multi=3)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_blockquoted_list(self, rule: MD030, config: MD030Config) -> None:
        """Lists inside blockquotes are not checked (known limitation)."""
        content = load_fixture("md030", "blockquoted_list.md")
        doc = Document(Path("blockquoted_list.md"), content)

        violations = rule.check(doc, config)

        # Blockquoted list lines start with "> " so the regex doesn't match
        assert len(violations) == 0
