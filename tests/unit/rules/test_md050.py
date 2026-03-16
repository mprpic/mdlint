from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md050 import MD050, MD050Config
from tests.conftest import load_fixture


class TestMD050:
    @pytest.fixture
    def rule(self) -> MD050:
        return MD050()

    @pytest.fixture
    def config(self) -> MD050Config:
        return MD050Config()

    def test_valid_consistent_style(self, rule: MD050, config: MD050Config) -> None:
        """Valid document with consistent strong style."""
        content = load_fixture("md050", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_mixed_styles(self, rule: MD050, config: MD050Config) -> None:
        """Invalid document with mixed strong styles."""
        content = load_fixture("md050", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD050"
        assert violations[0].line == 5
        assert violations[0].column == 15
        assert "asterisk" in violations[0].message
        assert "underscore" in violations[0].message

    def test_no_strong_text(self, rule: MD050, config: MD050Config) -> None:
        """Document without any strong text."""
        content = load_fixture("md050", "no_strong.md")
        doc = Document(Path("no_strong.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_config_asterisk_style(self, rule: MD050) -> None:
        """Enforce asterisk style via config."""
        config = MD050Config(style="asterisk")
        content = load_fixture("md050", "asterisk.md")
        doc = Document(Path("asterisk.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_config_asterisk_style_violation(self, rule: MD050) -> None:
        """Asterisk style config with underscore markers."""
        config = MD050Config(style="asterisk")
        content = load_fixture("md050", "underscore.md")
        doc = Document(Path("underscore.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 3
        assert "asterisk" in violations[0].message

    def test_config_underscore_style(self, rule: MD050) -> None:
        """Enforce underscore style via config."""
        config = MD050Config(style="underscore")
        content = load_fixture("md050", "underscore.md")
        doc = Document(Path("underscore.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_config_underscore_style_violation(self, rule: MD050) -> None:
        """Underscore style config with asterisk markers."""
        config = MD050Config(style="underscore")
        content = load_fixture("md050", "asterisk.md")
        doc = Document(Path("asterisk.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 3
        assert "underscore" in violations[0].message

    def test_consistent_first_asterisk(self, rule: MD050, config: MD050Config) -> None:
        """Consistent mode uses first strong style found (asterisks)."""
        content = load_fixture("md050", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        # First style is asterisk, so underscore should be violation
        assert len(violations) == 1
        assert "underscore" in violations[0].message

    def test_consistent_first_underscore(self, rule: MD050, config: MD050Config) -> None:
        """Consistent mode uses first strong style found (underscores)."""
        content = """\
# Test

This uses __underscores__ first.

Then uses **asterisks** later.
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        # First style is underscore, so asterisk should be violation
        assert len(violations) == 1
        assert violations[0].line == 5
        assert violations[0].column == 11
        assert "asterisk" in violations[0].message

    def test_intraword_underscores_no_false_positive(
        self, rule: MD050, config: MD050Config
    ) -> None:
        """Intra-word underscores are not parsed as strong emphasis."""
        content = load_fixture("md050", "intraword.md")
        doc = Document(Path("intraword.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiline_paragraph(self, rule: MD050, config: MD050Config) -> None:
        """Correct line/column for strong markers across paragraph lines."""
        content = load_fixture("md050", "multiline.md")
        doc = Document(Path("multiline.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 2
        assert violations[0].column == 5

    def test_intraword_underscores_before_strong(self, rule: MD050) -> None:
        """Correct line when intra-word __ text precedes actual strong marker."""
        config = MD050Config(style="asterisk")
        content = load_fixture("md050", "intraword_before_strong.md")
        doc = Document(Path("intraword_before_strong.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 2
        assert violations[0].column == 5

    def test_strong_in_list(self, rule: MD050, config: MD050Config) -> None:
        """Strong markers in list items."""
        content = load_fixture("md050", "list.md")
        doc = Document(Path("list.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 2
        assert violations[0].column == 11

    def test_strong_in_blockquote(self, rule: MD050, config: MD050Config) -> None:
        """Strong markers in blockquotes."""
        content = load_fixture("md050", "blockquote.md")
        doc = Document(Path("blockquote.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3

    def test_strong_in_heading(self, rule: MD050) -> None:
        """Strong markers in headings."""
        config = MD050Config(style="underscore")
        content = load_fixture("md050", "heading.md")
        doc = Document(Path("heading.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert violations[0].column == 14


class TestMD050Fix:
    @pytest.fixture
    def rule(self) -> MD050:
        return MD050()

    @pytest.fixture
    def config(self) -> MD050Config:
        return MD050Config()

    def test_fix_consistent_converts_to_first_style(self, rule: MD050, config: MD050Config) -> None:
        """Fix in consistent mode converts all strong to match the first marker."""
        content = load_fixture("md050", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []
        # First marker is **, so __ should become **
        assert "**underscores**" in result.split("\n")[4]

    def test_fix_returns_none_for_valid(self, rule: MD050, config: MD050Config) -> None:
        """Fix returns None when there are no violations."""
        content = load_fixture("md050", "valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_asterisk_style(self, rule: MD050) -> None:
        """Fix converts underscores to asterisks when asterisk style is configured."""
        config = MD050Config(style="asterisk")
        content = load_fixture("md050", "underscore.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_underscore_style(self, rule: MD050) -> None:
        """Fix converts asterisks to underscores when underscore style is configured."""
        config = MD050Config(style="underscore")
        content = load_fixture("md050", "asterisk.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_already_correct_style(self, rule: MD050) -> None:
        """Fix returns None when all strong already matches the configured style."""
        config = MD050Config(style="asterisk")
        content = load_fixture("md050", "asterisk.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_no_strong(self, rule: MD050, config: MD050Config) -> None:
        """Fix returns None for document without strong text."""
        content = load_fixture("md050", "no_strong.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_multiline(self, rule: MD050, config: MD050Config) -> None:
        """Fix replaces strong markers in multi-line paragraphs."""
        content = load_fixture("md050", "multiline.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_list(self, rule: MD050, config: MD050Config) -> None:
        """Fix replaces strong markers in list items."""
        content = load_fixture("md050", "list.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_blockquote(self, rule: MD050, config: MD050Config) -> None:
        """Fix replaces strong markers in blockquotes."""
        content = load_fixture("md050", "blockquote.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_empty_document(self, rule: MD050, config: MD050Config) -> None:
        """Fix returns None for empty document."""
        doc = Document(Path("empty.md"), "")
        result = rule.fix(doc, config)
        assert result is None

    def test_fixable_property(self, rule: MD050) -> None:
        """Rule reports as fixable."""
        assert rule.fixable is True
