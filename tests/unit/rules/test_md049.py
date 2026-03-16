from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md049 import MD049, MD049Config
from tests.conftest import load_fixture


class TestMD049:
    @pytest.fixture
    def rule(self) -> MD049:
        return MD049()

    @pytest.fixture
    def config(self) -> MD049Config:
        return MD049Config()

    def test_valid_consistent_emphasis(self, rule: MD049, config: MD049Config) -> None:
        """Valid document with consistent emphasis markers."""
        content = load_fixture("md049", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_mixed_emphasis(self, rule: MD049, config: MD049Config) -> None:
        """Invalid document with mixed emphasis markers."""
        content = load_fixture("md049", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD049"
        assert violations[0].line == 5
        assert violations[0].column == 15
        assert "underscore" in violations[0].message

    def test_no_emphasis(self, rule: MD049, config: MD049Config) -> None:
        """Document without emphasis."""
        content = load_fixture("md049", "no_emphasis.md")
        doc = Document(Path("no_emphasis.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_config_asterisk_style(self, rule: MD049) -> None:
        """Enforce asterisk style via config."""
        config = MD049Config(style="asterisk")
        content = load_fixture("md049", "asterisk.md")
        doc = Document(Path("asterisk.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_config_asterisk_style_violation(self, rule: MD049) -> None:
        """Asterisk style config with underscore emphasis."""
        config = MD049Config(style="asterisk")
        content = load_fixture("md049", "underscore.md")
        doc = Document(Path("underscore.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 4
        assert violations[0].line == 3
        assert violations[0].column == 15
        assert "asterisk" in violations[0].message

    def test_config_underscore_style(self, rule: MD049) -> None:
        """Enforce underscore style via config."""
        config = MD049Config(style="underscore")
        content = load_fixture("md049", "underscore.md")
        doc = Document(Path("underscore.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_config_underscore_style_violation(self, rule: MD049) -> None:
        """Underscore style config with asterisk emphasis."""
        config = MD049Config(style="underscore")
        content = load_fixture("md049", "asterisk.md")
        doc = Document(Path("asterisk.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 4
        assert violations[0].line == 3
        assert violations[0].column == 15
        assert "underscore" in violations[0].message

    def test_underscore_in_words_not_emphasis(self, rule: MD049, config: MD049Config) -> None:
        """Underscores inside words should not be treated as emphasis."""
        content = load_fixture("md049", "underscore_in_words.md")
        doc = Document(Path("underscore_in_words.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multi_line_paragraph(self, rule: MD049) -> None:
        """Emphasis in multi-line paragraph reports correct line number."""
        config = MD049Config(style="underscore")
        content = load_fixture("md049", "multi_line.md")
        doc = Document(Path("multi_line.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3
        assert violations[0].column == 6

    def test_code_block_emphasis_ignored(self, rule: MD049, config: MD049Config) -> None:
        """Emphasis markers inside code blocks should be ignored."""
        content = load_fixture("md049", "code_block.md")
        doc = Document(Path("code_block.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_code_span_emphasis_ignored(self, rule: MD049, config: MD049Config) -> None:
        """Emphasis markers inside code spans should be ignored."""
        content = load_fixture("md049", "code_span.md")
        doc = Document(Path("code_span.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_emphasis_same_line(self, rule: MD049) -> None:
        """Multiple emphasis markers on same line have correct columns."""
        config = MD049Config(style="underscore")
        content = load_fixture("md049", "multiple_same_line.md")
        doc = Document(Path("multiple_same_line.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 3
        assert violations[0].column == 1
        assert violations[1].column == 11
        assert violations[2].column == 21

    def test_intraword_emphasis_not_flagged(self, rule: MD049) -> None:
        """Intraword emphasis using asterisks is not flagged when underscore style is enforced."""
        config = MD049Config(style="underscore")
        content = load_fixture("md049", "intraword.md")
        doc = Document(Path("intraword.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_intraword_mixed_with_regular(self, rule: MD049) -> None:
        """Intraword emphasis is skipped but regular mismatches are still flagged."""
        config = MD049Config(style="underscore")
        doc = Document(Path("test.md"), "_regular_ and *a*1 and *wrong* emphasis.\n")

        violations = rule.check(doc, config)

        # *a*1 is intraword (not flagged), *wrong* is not (flagged)
        assert len(violations) == 1
        assert violations[0].column == 24

    def test_empty_document(self, rule: MD049, config: MD049Config) -> None:
        """Empty document produces no violations."""
        doc = Document(Path("empty.md"), "")

        violations = rule.check(doc, config)

        assert len(violations) == 0


class TestMD049Fix:
    @pytest.fixture
    def rule(self) -> MD049:
        return MD049()

    @pytest.fixture
    def config(self) -> MD049Config:
        return MD049Config()

    def test_fix_consistent_converts_to_first_style(self, rule: MD049, config: MD049Config) -> None:
        """Fix in consistent mode converts all emphasis to match the first marker."""
        content = load_fixture("md049", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []
        # First marker is *, so underscores should become asterisks
        assert "*italic*" in result.split("\n")[4]

    def test_fix_returns_none_for_valid(self, rule: MD049, config: MD049Config) -> None:
        """Fix returns None when there are no violations."""
        content = load_fixture("md049", "valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_asterisk_style(self, rule: MD049) -> None:
        """Fix converts underscores to asterisks when asterisk style is configured."""
        config = MD049Config(style="asterisk")
        content = load_fixture("md049", "underscore.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_underscore_style(self, rule: MD049) -> None:
        """Fix converts asterisks to underscores when underscore style is configured."""
        config = MD049Config(style="underscore")
        content = load_fixture("md049", "asterisk.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_already_correct_style(self, rule: MD049) -> None:
        """Fix returns None when all emphasis already matches the configured style."""
        config = MD049Config(style="asterisk")
        content = load_fixture("md049", "asterisk.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_no_emphasis(self, rule: MD049, config: MD049Config) -> None:
        """Fix returns None for document without emphasis."""
        content = load_fixture("md049", "no_emphasis.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_multiple_same_line(self, rule: MD049) -> None:
        """Fix replaces multiple emphasis markers on the same line."""
        config = MD049Config(style="underscore")
        content = load_fixture("md049", "multiple_same_line.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []
        assert result.startswith("_foo_ and _bar_ and _baz_")

    def test_fix_multi_line(self, rule: MD049) -> None:
        """Fix replaces emphasis in multi-line paragraphs."""
        config = MD049Config(style="underscore")
        content = load_fixture("md049", "multi_line.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_skips_intraword_emphasis(self, rule: MD049) -> None:
        """Fix does not convert intraword asterisks to underscores."""
        config = MD049Config(style="underscore")
        content = load_fixture("md049", "intraword.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_intraword_mixed_with_regular(self, rule: MD049) -> None:
        """Fix converts regular mismatches but skips intraword emphasis."""
        config = MD049Config(style="underscore")
        doc = Document(Path("test.md"), "_regular_ and *a*1 and *wrong* emphasis.\n")
        result = rule.fix(doc, config)
        assert result is not None
        assert "_wrong_" in result
        assert "*a*1" in result
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_empty_document(self, rule: MD049, config: MD049Config) -> None:
        """Fix returns None for empty document."""
        doc = Document(Path("empty.md"), "")
        result = rule.fix(doc, config)
        assert result is None

    def test_fixable_property(self, rule: MD049) -> None:
        """Rule reports as fixable."""
        assert rule.fixable is True
