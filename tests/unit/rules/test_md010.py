from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md010 import MD010, MD010Config
from tests.conftest import load_fixture


class TestMD010:
    @pytest.fixture
    def rule(self) -> MD010:
        return MD010()

    @pytest.fixture
    def config(self) -> MD010Config:
        return MD010Config()

    def test_valid_document(self, rule: MD010, config: MD010Config) -> None:
        """Valid document with no hard tabs passes the rule."""
        content = load_fixture("md010", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD010, config: MD010Config) -> None:
        """Invalid document with hard tabs triggers violations."""
        content = load_fixture("md010", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD010"
        assert violations[0].rule_name == "no-hard-tabs"
        assert "tab" in violations[0].message.lower()

    def test_no_tabs(self, rule: MD010, config: MD010Config) -> None:
        """Document without any tabs."""
        content = load_fixture("md010", "no_tabs.md")
        doc = Document(Path("no_tabs.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_code_blocks_checked_by_default(self, rule: MD010, config: MD010Config) -> None:
        """Code blocks are checked for tabs by default."""
        content = load_fixture("md010", "code_block.md")
        doc = Document(Path("code_block.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD010"

    def test_code_blocks_ignored_when_configured(self, rule: MD010) -> None:
        """Code blocks are ignored when code_blocks=False."""
        config = MD010Config(code_blocks=False)
        content = load_fixture("md010", "code_block.md")
        doc = Document(Path("code_block.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_column_position_reported(self, rule: MD010, config: MD010Config) -> None:
        """Tab position is correctly reported as column number."""
        content = "Text\twith tab"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert violations[0].column == 5  # Tab starts at column 5

    def test_multiple_tabs_on_same_line(self, rule: MD010, config: MD010Config) -> None:
        """Multiple tabs on the same line are reported separately."""
        content = "\tFirst\tSecond"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].column == 1
        assert violations[1].column == 7

    def test_inline_code_checked_by_default(self, rule: MD010, config: MD010Config) -> None:
        """Inline code spans are checked for tabs by default."""
        content = load_fixture("md010", "inline_code.md")
        doc = Document(Path("inline_code.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2

    def test_inline_code_ignored_when_code_blocks_false(self, rule: MD010) -> None:
        """Inline code spans are ignored when code_blocks=False."""
        config = MD010Config(code_blocks=False)
        content = load_fixture("md010", "inline_code.md")
        doc = Document(Path("inline_code.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].column == 26  # Tab outside the code span

    def test_indented_code_block_ignored_when_configured(self, rule: MD010) -> None:
        """Indented code blocks are ignored when code_blocks=False."""
        config = MD010Config(code_blocks=False)
        content = load_fixture("md010", "indented_code_block.md")
        doc = Document(Path("indented_code_block.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_empty_document(self, rule: MD010, config: MD010Config) -> None:
        """Empty document has no violations."""
        content = ""
        doc = Document(Path("empty.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0
