from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md007 import MD007, MD007Config
from tests.conftest import load_fixture


class TestMD007:
    @pytest.fixture
    def rule(self) -> MD007:
        return MD007()

    @pytest.fixture
    def config(self) -> MD007Config:
        return MD007Config()

    def test_valid_document(self, rule: MD007, config: MD007Config) -> None:
        """Valid document with correct 2-space indentation."""
        content = load_fixture("md007", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD007, config: MD007Config) -> None:
        """Invalid document with incorrect indentation."""
        content = load_fixture("md007", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD007"
        assert violations[0].line == 4
        assert "Expected 2 spaces, found 3" in violations[0].message
        assert violations[1].line == 6
        assert "Expected 2 spaces, found 4" in violations[1].message

    def test_custom_indent(self, rule: MD007) -> None:
        """Test with custom 4-space indentation."""
        content = load_fixture("md007", "indent_4.md")
        doc = Document(Path("indent_4.md"), content)
        config = MD007Config(indent=4)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_start_indented(self, rule: MD007) -> None:
        """Test with start_indented enabled."""
        content = load_fixture("md007", "start_indented.md")
        doc = Document(Path("start_indented.md"), content)
        config = MD007Config(start_indented=True, start_indent=2)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_mixed_list_types(self, rule: MD007, config: MD007Config) -> None:
        """Test that rule only applies to unordered sublists under unordered parents."""
        content = load_fixture("md007", "mixed_list.md")
        doc = Document(Path("mixed_list.md"), content)

        violations = rule.check(doc, config)

        # Rule should not flag unordered lists under ordered lists
        assert len(violations) == 0

    def test_no_lists(self, rule: MD007, config: MD007Config) -> None:
        """Document without lists."""
        content = load_fixture("md007", "no_lists.md")
        doc = Document(Path("no_lists.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_start_indented_violations(self, rule: MD007) -> None:
        """Non-indented top-level items should be flagged when start_indented is True."""
        content = load_fixture("md007", "start_indented_invalid.md")
        doc = Document(Path("start_indented_invalid.md"), content)
        config = MD007Config(start_indented=True)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 3
        assert "Expected 2 spaces, found 0" in violations[0].message
        assert violations[1].line == 4
        assert "Expected 2 spaces, found 0" in violations[1].message

    def test_custom_start_indent(self, rule: MD007) -> None:
        """Test start_indented with explicit start_indent different from indent."""
        content = load_fixture("md007", "start_indent_custom.md")
        doc = Document(Path("start_indent_custom.md"), content)
        config = MD007Config(indent=2, start_indented=True, start_indent=2)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_start_indent_defaults_to_indent(self, rule: MD007) -> None:
        """When start_indent is not set, it defaults to the indent value."""
        content = load_fixture("md007", "indent_4.md")
        doc = Document(Path("indent_4.md"), content)
        config = MD007Config(indent=4, start_indented=True)

        violations = rule.check(doc, config)

        # indent_4.md has top-level items at 0 indent, but start_indented expects 4
        assert len(violations) > 0
        assert "Expected 4 spaces, found 0" in violations[0].message

    def test_blockquote_list(self, rule: MD007, config: MD007Config) -> None:
        """Lists inside blockquotes should not produce false positives."""
        content = load_fixture("md007", "blockquote.md")
        doc = Document(Path("blockquote.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = MD007Config()

        assert config.indent == 2
        assert config.start_indented is False
        # start_indent defaults to indent value via __post_init__
        assert config.start_indent == 2

    def test_start_indent_inherits_custom_indent(self) -> None:
        """start_indent should default to indent when not explicitly set."""
        config = MD007Config(indent=4)

        assert config.start_indent == 4
