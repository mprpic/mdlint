from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md025 import MD025, MD025Config
from tests.conftest import load_fixture


class TestMD025:
    @pytest.fixture
    def rule(self) -> MD025:
        return MD025()

    @pytest.fixture
    def config(self) -> MD025Config:
        return MD025Config()

    def test_valid_single_h1(self, rule: MD025, config: MD025Config) -> None:
        """Valid document with single top-level heading."""
        content = load_fixture("md025", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_multiple_h1(self, rule: MD025, config: MD025Config) -> None:
        """Invalid document with multiple top-level headings."""
        content = load_fixture("md025", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD025"
        assert violations[0].line == 5
        assert "h1" in violations[0].message.lower()

    def test_no_headings(self, rule: MD025, config: MD025Config) -> None:
        """Document without headings."""
        doc = Document(Path("empty.md"), "Just some text without headings.\n")

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_only_lower_level_headings(self, rule: MD025, config: MD025Config) -> None:
        """Document with only h2+ headings."""
        content = "## Section 1\n\nContent.\n\n## Section 2\n"
        doc = Document(Path("h2_only.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_custom_level_h2(self, rule: MD025) -> None:
        """Custom config treating h2 as top-level heading."""
        config = MD025Config(level=2)
        content = "## First Section\n\nContent.\n\n## Second Section\n"
        doc = Document(Path("h2_multiple.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 5

    def test_three_h1_headings(self, rule: MD025, config: MD025Config) -> None:
        """Document with three h1 headings reports two violations."""
        content = "# First\n\n# Second\n\n# Third\n"
        doc = Document(Path("three_h1.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 3
        assert violations[1].line == 5

    def test_headings_inside_blockquote_ignored(self, rule: MD025, config: MD025Config) -> None:
        """Headings inside block quotes are not counted as top-level headings."""
        content = "# Title\n\n> # Quoted Heading\n\nSome content.\n"
        doc = Document(Path("blockquote.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_h1_with_blockquote_heading(self, rule: MD025, config: MD025Config) -> None:
        """Multiple top-level h1s are flagged even with blockquote headings present."""
        content = "# Title\n\n> # Quoted\n\n# Second Title\n"
        doc = Document(Path("blockquote_multi.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 5

    def test_setext_headings(self, rule: MD025, config: MD025Config) -> None:
        """Multiple setext-style h1 headings are flagged."""
        content = "Title\n=====\n\nAnother Title\n=============\n"
        doc = Document(Path("setext.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 4

    def test_mixed_atx_and_setext(self, rule: MD025, config: MD025Config) -> None:
        """Mixed ATX and setext h1 headings are flagged."""
        content = "# ATX Title\n\nSetext Title\n============\n"
        doc = Document(Path("mixed.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3

    def test_content_before_first_h1(self, rule: MD025, config: MD025Config) -> None:
        """Multiple h1 headings flagged even with content before the first one."""
        content = "Some introductory text.\n\n# First\n\n# Second\n"
        doc = Document(Path("content_before.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 5
