from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md041 import MD041, MD041Config
from tests.conftest import load_fixture


class TestMD041:
    @pytest.fixture
    def rule(self) -> MD041:
        return MD041()

    @pytest.fixture
    def config(self) -> MD041Config:
        return MD041Config()

    def test_valid_document(self, rule: MD041, config: MD041Config) -> None:
        """Valid document with first line as top-level heading."""
        content = load_fixture("md041", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD041, config: MD041Config) -> None:
        """Invalid document not starting with a heading."""
        content = load_fixture("md041", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD041"
        assert violations[0].rule_name == "first-line-heading"
        assert violations[0].line == 1
        assert violations[0].column == 1
        assert violations[0].context == "This document does not start with a heading."

    def test_empty_document(self, rule: MD041, config: MD041Config) -> None:
        """Empty document should not trigger a violation."""
        doc = Document(Path("empty.md"), "")

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_whitespace_only(self, rule: MD041, config: MD041Config) -> None:
        """Whitespace-only document should not trigger a violation."""
        doc = Document(Path("whitespace.md"), "   \n\n  \n")

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_heading_after_blank_lines(self, rule: MD041, config: MD041Config) -> None:
        """Heading preceded by blank lines is valid."""
        content = "\n\n# Title\n\nContent.\n"
        doc = Document(Path("blank_start.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_h2_first_fails(self, rule: MD041, config: MD041Config) -> None:
        """Document starting with h2 instead of h1 triggers violation."""
        content = load_fixture("md041", "h2_first.md")
        doc = Document(Path("h2_first.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert violations[0].column == 1
        assert violations[0].context == "## Subheading"
        assert violations[0].message == "First heading should be h1, found h2"

    def test_custom_level_h2(self, rule: MD041) -> None:
        """Custom config expecting h2 as first heading."""
        config = MD041Config(level=2)
        content = load_fixture("md041", "h2_first.md")
        doc = Document(Path("h2_first.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_custom_level_h2_with_h1(self, rule: MD041) -> None:
        """Custom config expecting h2, but h1 found triggers violation."""
        config = MD041Config(level=2)
        content = load_fixture("md041", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].message == "First heading should be h2, found h1"
        assert violations[0].context == "# Document Title"

    def test_front_matter_with_title(self, rule: MD041, config: MD041Config) -> None:
        """Front matter with title key should satisfy the rule."""
        content = load_fixture("md041", "front_matter_title.md")
        doc = Document(Path("front_matter_title.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_front_matter_without_title(self, rule: MD041, config: MD041Config) -> None:
        """Front matter without title key should trigger violation."""
        content = load_fixture("md041", "front_matter_no_title.md")
        doc = Document(Path("front_matter_no_title.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 6
        assert violations[0].column == 1
        assert violations[0].context == "This content comes first without a title."

    def test_front_matter_with_heading(self, rule: MD041, config: MD041Config) -> None:
        """Front matter without title but followed by heading is valid."""
        content = load_fixture("md041", "front_matter_heading.md")
        doc = Document(Path("front_matter_heading.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_custom_front_matter_title_pattern(self, rule: MD041) -> None:
        """Custom front matter title pattern matches alternative keys."""
        config = MD041Config(front_matter_title=r"^\s*name\s*:")
        content = load_fixture("md041", "front_matter_custom.md")
        doc = Document(Path("front_matter_custom.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_disabled_front_matter_title(self, rule: MD041) -> None:
        """Empty front_matter_title disables front matter title check."""
        config = MD041Config(front_matter_title="")
        content = load_fixture("md041", "front_matter_disabled.md")
        doc = Document(Path("front_matter_disabled.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_setext_heading(self, rule: MD041, config: MD041Config) -> None:
        """Setext-style h1 heading on first line is valid."""
        content = load_fixture("md041", "setext_h1.md")
        doc = Document(Path("setext_h1.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_setext_h2_first_fails(self, rule: MD041, config: MD041Config) -> None:
        """Setext-style h2 on first line triggers violation."""
        content = load_fixture("md041", "setext_h2.md")
        doc = Document(Path("setext_h2.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert violations[0].column == 1
        assert violations[0].context == "Subsection"
        assert violations[0].message == "First heading should be h1, found h2"

    # --- HTML heading tests ---

    def test_html_h1_heading(self, rule: MD041, config: MD041Config) -> None:
        """HTML h1 heading as first content is valid."""
        content = load_fixture("md041", "html_h1.md")
        doc = Document(Path("html_h1.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_html_h1_with_attributes(self, rule: MD041, config: MD041Config) -> None:
        """HTML h1 heading with attributes is valid."""
        content = load_fixture("md041", "html_h1_attr.md")
        doc = Document(Path("html_h1_attr.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_html_h2_heading_fails(self, rule: MD041, config: MD041Config) -> None:
        """HTML h2 heading triggers violation when h1 expected."""
        content = load_fixture("md041", "html_h2.md")
        doc = Document(Path("html_h2.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert violations[0].column == 1
        assert violations[0].message == "First heading should be h1, found h2"
        assert violations[0].context == "<h2>Subsection</h2>"

    def test_html_heading_custom_level(self, rule: MD041) -> None:
        """HTML heading matching custom level is valid."""
        config = MD041Config(level=2)
        content = load_fixture("md041", "html_h2.md")
        doc = Document(Path("html_h2.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    # --- HTML comment tests ---

    def test_html_comment_before_heading(self, rule: MD041, config: MD041Config) -> None:
        """HTML comments before heading are skipped."""
        content = load_fixture("md041", "comment_heading.md")
        doc = Document(Path("comment_heading.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_html_comment_before_non_heading(self, rule: MD041, config: MD041Config) -> None:
        """HTML comment followed by non-heading content triggers violation."""
        content = load_fixture("md041", "comment_no_heading.md")
        doc = Document(Path("comment_no_heading.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3
        assert violations[0].column == 1
        assert violations[0].context == "Not a heading."

    # --- allow_preamble tests ---

    def test_allow_preamble_with_heading(self, rule: MD041) -> None:
        """Preamble content before heading is allowed when enabled."""
        config = MD041Config(allow_preamble=True)
        content = load_fixture("md041", "preamble_heading.md")
        doc = Document(Path("preamble_heading.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_allow_preamble_wrong_level(self, rule: MD041) -> None:
        """Preamble allowed but first heading is wrong level."""
        config = MD041Config(allow_preamble=True)
        content = load_fixture("md041", "preamble_wrong_level.md")
        doc = Document(Path("preamble_wrong_level.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3
        assert violations[0].column == 1
        assert violations[0].context == "## Subtitle"
        assert violations[0].message == "First heading should be h1, found h2"

    def test_allow_preamble_no_heading(self, rule: MD041) -> None:
        """Preamble allowed but no heading at all produces no violation."""
        config = MD041Config(allow_preamble=True)
        content = load_fixture("md041", "preamble_no_heading.md")
        doc = Document(Path("preamble_no_heading.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_allow_preamble_disabled(self, rule: MD041, config: MD041Config) -> None:
        """Preamble before heading triggers violation when disabled (default)."""
        content = load_fixture("md041", "preamble_heading.md")
        doc = Document(Path("preamble_heading.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert violations[0].column == 1
        assert violations[0].context == "Some preamble text."

    def test_allow_preamble_with_html_heading(self, rule: MD041) -> None:
        """Preamble content before HTML heading is allowed when enabled."""
        config = MD041Config(allow_preamble=True)
        content = load_fixture("md041", "preamble_html_heading.md")
        doc = Document(Path("preamble_html_heading.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    # --- level validation tests ---

    def test_level_out_of_range_defaults_to_one(self) -> None:
        """Out-of-range level values default to 1."""
        assert MD041Config(level=0).level == 1
        assert MD041Config(level=7).level == 1
        assert MD041Config(level=-1).level == 1
