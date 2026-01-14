from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md019 import MD019, MD019Config
from tests.conftest import load_fixture


class TestMD019:
    @pytest.fixture
    def rule(self) -> MD019:
        return MD019()

    @pytest.fixture
    def config(self) -> MD019Config:
        return MD019Config()

    def test_valid_document(self, rule: MD019, config: MD019Config) -> None:
        """Valid document with single space after hash passes."""
        content = load_fixture("md019", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD019, config: MD019Config) -> None:
        """Invalid document with multiple spaces triggers violations."""
        content = load_fixture("md019", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 3
        assert violations[0].rule_id == "MD019"
        assert violations[0].line == 1
        assert violations[1].line == 3
        assert violations[2].line == 5

    def test_no_headings(self, rule: MD019, config: MD019Config) -> None:
        """Document without headings passes."""
        content = load_fixture("md019", "no_headings.md")
        doc = Document(Path("no_headings.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_setext_headings(self, rule: MD019, config: MD019Config) -> None:
        """Setext headings are not checked (no hash marks)."""
        content = load_fixture("md019", "setext_heading.md")
        doc = Document(Path("setext.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_mixed_valid_invalid(self, rule: MD019, config: MD019Config) -> None:
        """Only invalid headings are flagged."""
        content = load_fixture("md019", "mixed_valid_invalid.md")
        doc = Document(Path("mixed.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3
        assert "Multiple spaces" in violations[0].message

    def test_violation_details(self, rule: MD019, config: MD019Config) -> None:
        """Violation includes correct details."""
        content = load_fixture("md019", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert violations[0].rule_id == "MD019"
        assert violations[0].rule_name == "no-multiple-space-atx"
        assert violations[0].column == 1
        assert "#  Heading 1" in violations[0].context

    def test_code_blocks_ignored(self, rule: MD019, config: MD019Config) -> None:
        """Hash-prefixed lines inside code blocks are not flagged."""
        content = "# Valid Heading\n\n```\n#  Not a heading\n##   Also not a heading\n```\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_three_or_more_spaces(self, rule: MD019, config: MD019Config) -> None:
        """Headings with three or more spaces after hash are flagged."""
        content = "#   Three spaces\n\n##    Four spaces\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 1
        assert violations[1].line == 3
