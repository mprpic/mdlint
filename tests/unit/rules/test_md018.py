from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md018 import MD018, MD018Config
from tests.conftest import load_fixture


class TestMD018:
    @pytest.fixture
    def rule(self) -> MD018:
        return MD018()

    @pytest.fixture
    def config(self) -> MD018Config:
        return MD018Config()

    def test_valid_headings_with_space(self, rule: MD018, config: MD018Config) -> None:
        """Valid document with proper spacing after hash."""
        content = load_fixture("md018", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_headings_missing_space(self, rule: MD018, config: MD018Config) -> None:
        """Invalid document with missing space after hash."""
        content = load_fixture("md018", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 3
        assert violations[0].rule_id == "MD018"
        assert violations[0].line == 1
        assert violations[0].column == 1
        assert "space" in violations[0].message.lower()
        assert violations[1].line == 3
        assert violations[2].line == 5

    def test_code_blocks_ignored(self, rule: MD018, config: MD018Config) -> None:
        """Lines inside code blocks should be ignored."""
        content = load_fixture("md018", "code_blocks.md")
        doc = Document(Path("code_blocks.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_no_headings(self, rule: MD018, config: MD018Config) -> None:
        """Document without headings."""
        content = load_fixture("md018", "no_headings.md")
        doc = Document(Path("no_headings.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_only_hash_characters(self, rule: MD018, config: MD018Config) -> None:
        """Lines with only hash characters should be ignored."""
        content = "###\n\n####\n"
        doc = Document(Path("only_hash.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_mixed_valid_invalid(self, rule: MD018, config: MD018Config) -> None:
        """Mix of valid and invalid headings."""
        content = "# Valid\n\n##Invalid\n\n### Also Valid\n"
        doc = Document(Path("mixed.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3
        assert violations[0].context == "##Invalid"

    def test_html_blocks_ignored(self, rule: MD018, config: MD018Config) -> None:
        """Lines inside HTML blocks should be ignored."""
        content = load_fixture("md018", "html_block.md")
        doc = Document(Path("html_block.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_hash_in_middle_of_line(self, rule: MD018, config: MD018Config) -> None:
        """Hash characters in the middle of a line are not headings."""
        content = "This is a #tag and not a heading\n\nAnother line with ##double hash\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0
