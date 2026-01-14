from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md054 import MD054, MD054Config
from tests.conftest import load_fixture


class TestMD054:
    @pytest.fixture
    def rule(self) -> MD054:
        return MD054()

    @pytest.fixture
    def config(self) -> MD054Config:
        return MD054Config()

    def test_valid_document(self, rule: MD054, config: MD054Config) -> None:
        """Valid document passes the rule with all styles allowed."""
        content = load_fixture("md054", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_autolink_disallowed(self, rule: MD054) -> None:
        """Autolinks trigger violations when disallowed."""
        config = MD054Config(autolink=False, inline=False)
        content = load_fixture("md054", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD054"
        assert "autolink" in violations[0].message.lower()

    def test_autolink_allowed(self, rule: MD054, config: MD054Config) -> None:
        """Autolinks pass when allowed."""
        content = load_fixture("md054", "autolink.md")
        doc = Document(Path("autolink.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_autolink_disallowed(self, rule: MD054) -> None:
        """Autolinks trigger violations when disallowed."""
        config = MD054Config(autolink=False)
        content = load_fixture("md054", "autolink.md")
        doc = Document(Path("autolink.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD054"

    def test_inline_allowed(self, rule: MD054, config: MD054Config) -> None:
        """Inline links pass when allowed."""
        content = load_fixture("md054", "inline.md")
        doc = Document(Path("inline.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_inline_disallowed(self, rule: MD054) -> None:
        """Inline links trigger violations when disallowed."""
        config = MD054Config(inline=False)
        content = load_fixture("md054", "inline.md")
        doc = Document(Path("inline.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD054"

    def test_full_reference_allowed(self, rule: MD054, config: MD054Config) -> None:
        """Full reference links pass when allowed."""
        content = load_fixture("md054", "full_reference.md")
        doc = Document(Path("full_reference.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_full_reference_disallowed(self, rule: MD054) -> None:
        """Full reference links trigger violations when disallowed."""
        config = MD054Config(full=False)
        content = load_fixture("md054", "full_reference.md")
        doc = Document(Path("full_reference.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD054"

    def test_collapsed_reference_allowed(self, rule: MD054, config: MD054Config) -> None:
        """Collapsed reference links pass when allowed."""
        content = load_fixture("md054", "collapsed_reference.md")
        doc = Document(Path("collapsed_reference.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_collapsed_reference_disallowed(self, rule: MD054) -> None:
        """Collapsed reference links trigger violations when disallowed."""
        config = MD054Config(collapsed=False)
        content = load_fixture("md054", "collapsed_reference.md")
        doc = Document(Path("collapsed_reference.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD054"

    def test_shortcut_reference_allowed(self, rule: MD054, config: MD054Config) -> None:
        """Shortcut reference links pass when allowed."""
        content = load_fixture("md054", "shortcut_reference.md")
        doc = Document(Path("shortcut_reference.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_shortcut_reference_disallowed(self, rule: MD054) -> None:
        """Shortcut reference links trigger violations when disallowed."""
        config = MD054Config(shortcut=False)
        content = load_fixture("md054", "shortcut_reference.md")
        doc = Document(Path("shortcut_reference.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD054"

    def test_url_inline_allowed(self, rule: MD054, config: MD054Config) -> None:
        """URL inline links pass when allowed."""
        content = load_fixture("md054", "url_inline.md")
        doc = Document(Path("url_inline.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_url_inline_disallowed(self, rule: MD054) -> None:
        """URL inline links trigger violations when url_inline is false."""
        config = MD054Config(url_inline=False)
        content = load_fixture("md054", "url_inline.md")
        doc = Document(Path("url_inline.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD054"
        assert "autolink" in violations[0].message.lower()

    def test_all_allowed_no_violations(self, rule: MD054) -> None:
        """When all styles are allowed, no violations are reported."""
        config = MD054Config(
            autolink=True,
            inline=True,
            full=True,
            collapsed=True,
            shortcut=True,
            url_inline=True,
        )
        content = load_fixture("md054", "all_styles.md")
        doc = Document(Path("all_styles.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_links_in_code_blocks_ignored(self, rule: MD054) -> None:
        """Links inside code blocks should be ignored."""
        config = MD054Config(autolink=False)
        content = load_fixture("md054", "code_blocks.md")
        doc = Document(Path("code_blocks.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_links_in_inline_code_ignored(self, rule: MD054) -> None:
        """Links inside inline code should be ignored."""
        config = MD054Config(inline=False)
        content = load_fixture("md054", "inline_code.md")
        doc = Document(Path("inline_code.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_url_inline_disallowed_autolink_also_disallowed(self, rule: MD054) -> None:
        """URL inline check does not fire when autolinks are also disabled."""
        config = MD054Config(url_inline=False, autolink=False)
        content = load_fixture("md054", "url_inline.md")
        doc = Document(Path("url_inline.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_url_inline_with_title_not_flagged(self, rule: MD054) -> None:
        """URL inline links with a title are not flagged as url_inline."""
        config = MD054Config(url_inline=False)
        content = load_fixture("md054", "url_inline_with_title.md")
        doc = Document(Path("url_inline_with_title.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_violation_column_numbers(self, rule: MD054) -> None:
        """Violations report correct column numbers."""
        config = MD054Config(autolink=False, inline=False)
        content = load_fixture("md054", "column_numbers.md")
        doc = Document(Path("column_numbers.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 3
        assert violations[0].column == 7
        assert violations[1].line == 5
        assert violations[1].column == 4

    def test_parentheses_in_url(self, rule: MD054) -> None:
        """Inline links with parentheses in URLs are handled correctly."""
        config = MD054Config(inline=False)
        content = load_fixture("md054", "parentheses_in_url.md")
        doc = Document(Path("parentheses_in_url.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3
        assert violations[0].column == 1
        assert "Inline link" in violations[0].message

    def test_multiple_links_on_same_line(self, rule: MD054) -> None:
        """Multiple links on the same line are each checked."""
        config = MD054Config(inline=False)
        content = load_fixture("md054", "multiple_links.md")
        doc = Document(Path("multiple_links.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].column == 5
        assert violations[1].column == 30
