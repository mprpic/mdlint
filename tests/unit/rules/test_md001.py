from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md001 import MD001, MD001Config
from tests.conftest import load_fixture


class TestMD001:
    @pytest.fixture
    def rule(self) -> MD001:
        return MD001()

    @pytest.fixture
    def config(self) -> MD001Config:
        return MD001Config()

    def test_valid_heading_increments(self, rule: MD001, config: MD001Config) -> None:
        """Valid document with proper heading increments."""
        content = load_fixture("md001", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_heading_increments(self, rule: MD001, config: MD001Config) -> None:
        """Invalid document with skipped heading levels."""
        content = load_fixture("md001", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD001"
        assert violations[0].line == 3
        assert "h1 to h3" in violations[0].message
        assert violations[1].line == 5
        assert "h3 to h6" in violations[1].message

    def test_no_headings(self, rule: MD001, config: MD001Config) -> None:
        """Document without headings."""
        content = load_fixture("md001", "no_headings.md")
        doc = Document(Path("no_headings.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_single_heading(self, rule: MD001, config: MD001Config) -> None:
        """Document with single heading."""
        content = load_fixture("md001", "single_heading.md")
        doc = Document(Path("single.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_decreasing_levels_allowed(self, rule: MD001, config: MD001Config) -> None:
        """Decreasing heading levels are allowed."""
        content = load_fixture("md001", "decreasing_levels.md")
        doc = Document(Path("decreasing.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_setext_headings_valid(self, rule: MD001, config: MD001Config) -> None:
        """Valid setext-style headings with proper increments."""
        content = load_fixture("md001", "setext_valid.md")
        doc = Document(Path("setext_valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_setext_headings_invalid(self, rule: MD001, config: MD001Config) -> None:
        """Invalid setext-style headings with skipped levels."""
        content = load_fixture("md001", "setext_invalid.md")
        doc = Document(Path("setext_invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 4
        assert "h1 to h3" in violations[0].message
        assert violations[1].line == 6
        assert "h3 to h6" in violations[1].message

    def test_starting_at_h2(self, rule: MD001, config: MD001Config) -> None:
        """Document starting at H2 is valid."""
        content = load_fixture("md001", "starting_h2.md")
        doc = Document(Path("starting_h2.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_front_matter_title_valid(self, rule: MD001, config: MD001Config) -> None:
        """Front matter title acts as implicit H1, so H2 is expected first."""
        content = load_fixture("md001", "front_matter_title.md")
        doc = Document(Path("front_matter_title.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_front_matter_title_invalid(self, rule: MD001, config: MD001Config) -> None:
        """Front matter title as H1 means H3 first heading is a violation."""
        content = load_fixture("md001", "front_matter_title_invalid.md")
        doc = Document(Path("front_matter_title_invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 6
        assert "h1 to h3" in violations[0].message

    def test_front_matter_no_title(self, rule: MD001, config: MD001Config) -> None:
        """Front matter without title does not affect heading checks."""
        content = load_fixture("md001", "front_matter_no_title.md")
        doc = Document(Path("front_matter_no_title.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_front_matter_title_disabled(self, rule: MD001) -> None:
        """Disabling front_matter_title ignores title in front matter."""
        content = load_fixture("md001", "front_matter_title_invalid.md")
        doc = Document(Path("front_matter_title_invalid.md"), content)
        config = MD001Config(front_matter_title="")

        violations = rule.check(doc, config)

        assert len(violations) == 0
