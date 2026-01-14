from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md036 import MD036, MD036Config
from tests.conftest import load_fixture


class TestMD036:
    @pytest.fixture
    def rule(self) -> MD036:
        return MD036()

    @pytest.fixture
    def config(self) -> MD036Config:
        return MD036Config()

    def test_valid_document(self, rule: MD036, config: MD036Config) -> None:
        """Valid document passes the rule."""
        content = load_fixture("md036", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD036, config: MD036Config) -> None:
        """Invalid document triggers violations."""
        content = load_fixture("md036", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 3
        assert violations[0].rule_id == "MD036"
        assert violations[0].line == 3
        assert violations[1].line == 7
        assert violations[2].line == 11

    def test_bold_emphasis_as_heading(self, rule: MD036, config: MD036Config) -> None:
        """Bold text used as heading is flagged."""
        content = "**Section Title**\n\nSome content here.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "emphasis" in violations[0].message.lower()

    def test_italic_emphasis_as_heading(self, rule: MD036, config: MD036Config) -> None:
        """Italic text used as heading is flagged."""
        content = "_Section Title_\n\nSome content here.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_emphasis_with_trailing_punctuation_allowed(
        self, rule: MD036, config: MD036Config
    ) -> None:
        """Emphasis ending with punctuation is not flagged."""
        content = "**This is a sentence.**\n\n_Another sentence!_\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_emphasis_within_paragraph_allowed(self, rule: MD036, config: MD036Config) -> None:
        """Emphasis within a paragraph with other text is allowed."""
        content = "This is **bold** text in a paragraph.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_custom_punctuation(self, rule: MD036) -> None:
        """Custom punctuation configuration."""
        config = MD036Config(punctuation=".")
        content = "**This ends with period.**\n\n**This ends with colon:**\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        # Colon is not in custom punctuation, so it triggers
        assert len(violations) == 1
        assert violations[0].line == 3

    def test_empty_punctuation(self, rule: MD036) -> None:
        """Empty punctuation means all emphasis-only paragraphs are flagged."""
        config = MD036Config(punctuation="")
        content = "**This ends with period.**\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_multiline_emphasis_not_flagged(self, rule: MD036, config: MD036Config) -> None:
        """Multi-line emphasis paragraphs are not flagged."""
        content = "**This is a long\nemphasis paragraph**\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_emphasis_in_list_items_not_flagged(self, rule: MD036, config: MD036Config) -> None:
        """Emphasis inside list items is not flagged."""
        content = "- **Bold list item**\n- *Italic list item*\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_emphasis_in_blockquote_not_flagged(self, rule: MD036, config: MD036Config) -> None:
        """Emphasis inside blockquotes is not flagged."""
        content = "> **Bold in blockquote**\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_emphasis_blocks_not_flagged(self, rule: MD036, config: MD036Config) -> None:
        """Multiple separate emphasis blocks in one paragraph are not flagged."""
        content = "**text1** **text2**\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_underscore_bold_as_heading(self, rule: MD036, config: MD036Config) -> None:
        """Underscore-style bold used as heading is flagged."""
        content = "__Section Title__\n\nSome content here.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1

    def test_no_paragraphs(self, rule: MD036, config: MD036Config) -> None:
        """Document without paragraphs."""
        content = "# Just a heading\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0
