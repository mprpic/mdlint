from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md024 import MD024, MD024Config
from tests.conftest import load_fixture


class TestMD024:
    @pytest.fixture
    def rule(self) -> MD024:
        return MD024()

    @pytest.fixture
    def config(self) -> MD024Config:
        return MD024Config()

    def test_valid_unique_headings(self, rule: MD024, config: MD024Config) -> None:
        """Valid document with unique headings."""
        content = load_fixture("md024", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_duplicate_headings(self, rule: MD024, config: MD024Config) -> None:
        """Invalid document with duplicate heading content."""
        content = load_fixture("md024", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD024"
        assert violations[0].rule_name == "no-duplicate-heading"
        assert violations[0].line == 3
        assert violations[0].column == 1
        assert violations[0].message == 'Duplicate heading "Some text"'
        assert violations[0].context == "## Some text"
        assert violations[1].line == 5
        assert violations[1].column == 1
        assert violations[1].message == 'Duplicate heading "Some text"'

    def test_no_headings(self, rule: MD024, config: MD024Config) -> None:
        """Document without headings."""
        content = load_fixture("md024", "no_headings.md")
        doc = Document(Path("no_headings.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_single_heading(self, rule: MD024, config: MD024Config) -> None:
        """Document with single heading."""
        content = load_fixture("md024", "single_heading.md")
        doc = Document(Path("single.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_siblings_only_allows_different_sections(self, rule: MD024) -> None:
        """With siblings_only, duplicate headings in different sections are allowed."""
        config = MD024Config(siblings_only=True)
        content = load_fixture("md024", "siblings_only_valid.md")
        doc = Document(Path("siblings_only_valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_siblings_only_flags_same_section_duplicates(self, rule: MD024) -> None:
        """With siblings_only, duplicate headings in the same section are flagged."""
        config = MD024Config(siblings_only=True)
        content = load_fixture("md024", "siblings_only_invalid.md")
        doc = Document(Path("siblings_only_invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 7
        assert "Features" in violations[0].message

    def test_siblings_only_false_flags_all_duplicates(self, rule: MD024) -> None:
        """With default siblings_only=False, all duplicate headings are flagged."""
        config = MD024Config(siblings_only=False)
        content = load_fixture("md024", "siblings_only_valid.md")
        doc = Document(Path("changelog.md"), content)

        violations = rule.check(doc, config)

        # "Features" appears twice and "Bug fixes" appears twice
        assert len(violations) == 2

    def test_siblings_only_flags_duplicates_with_deeper_between(self, rule: MD024) -> None:
        """With siblings_only, duplicates are flagged even with deeper headings between them."""
        config = MD024Config(siblings_only=True)
        content = load_fixture("md024", "siblings_deeper_between.md")
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 9
        assert violations[0].message == 'Duplicate heading "Section A"'

    def test_setext_duplicate_headings(self, rule: MD024, config: MD024Config) -> None:
        """Duplicate setext-style headings are flagged."""
        content = load_fixture("md024", "setext_duplicate.md")
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 6
        assert violations[0].message == 'Duplicate heading "Heading"'

    def test_closed_atx_matches_open_atx(self, rule: MD024, config: MD024Config) -> None:
        """Closed ATX heading (## Heading ##) matches open ATX (## Heading)."""
        content = load_fixture("md024", "closed_atx.md")
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3
        assert violations[0].message == 'Duplicate heading "Heading"'

    def test_mixed_atx_and_setext(self, rule: MD024, config: MD024Config) -> None:
        """Duplicate headings across ATX and setext styles are flagged."""
        content = load_fixture("md024", "mixed_styles.md")
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 4
        assert violations[0].message == 'Duplicate heading "Heading"'
