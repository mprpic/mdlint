from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md023 import MD023, MD023Config
from tests.conftest import load_fixture


class TestMD023:
    @pytest.fixture
    def rule(self) -> MD023:
        return MD023()

    @pytest.fixture
    def config(self) -> MD023Config:
        return MD023Config()

    def test_valid_headings_at_start(self, rule: MD023, config: MD023Config) -> None:
        """Valid document with headings starting at beginning of line."""
        content = load_fixture("md023", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_indented_headings(self, rule: MD023, config: MD023Config) -> None:
        """Invalid document with indented ATX and setext headings."""
        content = load_fixture("md023", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 5
        assert violations[0].rule_id == "MD023"
        assert violations[0].line == 1
        assert violations[0].column == 1
        assert "beginning" in violations[0].message.lower()
        assert violations[1].line == 3
        assert violations[2].line == 5
        # Setext headings
        assert violations[3].line == 7
        assert violations[4].line == 10

    def test_invalid_indented_setext_headings(self, rule: MD023, config: MD023Config) -> None:
        """Indented setext-style headings should be flagged."""
        content = "  Setext Heading\n================\n"
        doc = Document(Path("setext.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert "Setext Heading" in violations[0].context

    def test_code_blocks_ignored(self, rule: MD023, config: MD023Config) -> None:
        """Lines inside code blocks should be ignored."""
        content = load_fixture("md023", "code_blocks.md")
        doc = Document(Path("code_blocks.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_indented_code_block_not_flagged(self, rule: MD023, config: MD023Config) -> None:
        """4-space indented lines are code blocks, not headings."""
        content = "    # This is a code block\n\n    ## Also a code block\n"
        doc = Document(Path("code.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_no_headings(self, rule: MD023, config: MD023Config) -> None:
        """Document without headings."""
        content = "Just some text.\n\nMore text.\n"
        doc = Document(Path("no_headings.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_mixed_valid_invalid(self, rule: MD023, config: MD023Config) -> None:
        """Mix of valid and invalid headings."""
        content = "# Valid\n\n  ## Invalid\n\n### Also Valid\n"
        doc = Document(Path("mixed.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3
        assert "  ## Invalid" in violations[0].context

    def test_headings_inside_list_items_not_flagged(self, rule: MD023, config: MD023Config) -> None:
        """Headings inside list items should not be flagged."""
        content = load_fixture("md023", "list_items.md")
        doc = Document(Path("list_items.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_headings_in_blockquotes_not_flagged(self, rule: MD023, config: MD023Config) -> None:
        """Headings inside blockquotes should not be flagged."""
        content = "> # Heading in blockquote\n\n > ## Indented blockquote heading\n"
        doc = Document(Path("blockquote.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_fix_corrects_invalid(self, rule: MD023, config: MD023Config) -> None:
        """Fix removes leading whitespace from indented headings."""
        content = load_fixture("md023", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_returns_none_for_valid(self, rule: MD023, config: MD023Config) -> None:
        """Fix returns None when no headings need fixing."""
        content = load_fixture("md023", "valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_preserves_code_blocks(self, rule: MD023, config: MD023Config) -> None:
        """Fix does not modify indented lines inside code blocks."""
        content = load_fixture("md023", "code_blocks.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_preserves_list_items(self, rule: MD023, config: MD023Config) -> None:
        """Fix does not modify headings inside list items."""
        content = load_fixture("md023", "list_items.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_mixed_valid_invalid(self, rule: MD023, config: MD023Config) -> None:
        """Fix only strips indentation from invalid headings."""
        content = "# Valid\n\n  ## Invalid\n\n### Also Valid\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert result == "# Valid\n\n## Invalid\n\n### Also Valid\n"

    def test_fix_setext_heading(self, rule: MD023, config: MD023Config) -> None:
        """Fix strips indentation from setext-style headings."""
        content = "  Setext Heading\n================\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert result == "Setext Heading\n================\n"
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []
