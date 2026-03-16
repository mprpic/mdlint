from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md035 import MD035, MD035Config
from tests.conftest import load_fixture


class TestMD035:
    @pytest.fixture
    def rule(self) -> MD035:
        return MD035()

    @pytest.fixture
    def config(self) -> MD035Config:
        return MD035Config()

    def test_valid_document(self, rule: MD035, config: MD035Config) -> None:
        """Valid document with consistent horizontal rules passes."""
        content = load_fixture("md035", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD035, config: MD035Config) -> None:
        """Document with inconsistent horizontal rules triggers violations."""
        content = load_fixture("md035", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD035"
        assert violations[0].line == 9
        assert "Expected '---'" in violations[0].message
        assert "'***'" in violations[0].message

    def test_no_horizontal_rules(self, rule: MD035, config: MD035Config) -> None:
        """Document without horizontal rules passes."""
        content = "# Heading\n\nSome text.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_single_horizontal_rule(self, rule: MD035, config: MD035Config) -> None:
        """Document with single horizontal rule passes."""
        content = "# Heading\n\n---\n\nSome text.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_consistent_rules(self, rule: MD035, config: MD035Config) -> None:
        """Multiple consistent horizontal rules pass."""
        content = "Text\n\n***\n\nMore text\n\n***\n\nEnd\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_inconsistent_rules(self, rule: MD035, config: MD035Config) -> None:
        """Multiple inconsistent horizontal rules trigger violations."""
        content = "Text\n\n---\n\nMore\n\n***\n\nEven more\n\n- - -\n\nEnd\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 7
        assert violations[1].line == 11

    def test_specific_style_dashes(self, rule: MD035) -> None:
        """Specific style '---' enforces exact match."""
        config = MD035Config(style="---")
        content = "Text\n\n***\n\n---\n\nEnd\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3
        assert "Expected '---'" in violations[0].message

    def test_specific_style_asterisks(self, rule: MD035) -> None:
        """Specific style '***' enforces exact match."""
        config = MD035Config(style="***")
        content = "Text\n\n---\n\nMore\n\n***\n\nEnd\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3
        assert "Expected '***'" in violations[0].message

    def test_specific_style_spaced(self, rule: MD035) -> None:
        """Specific style with spaces enforces exact match."""
        config = MD035Config(style="- - -")
        content = "Text\n\n---\n\n- - -\n\nEnd\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3

    def test_all_match_specific_style(self, rule: MD035) -> None:
        """All horizontal rules matching specific style passes."""
        config = MD035Config(style="***")
        content = "Text\n\n***\n\nMore\n\n***\n\nEnd\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_different_lengths(self, rule: MD035, config: MD035Config) -> None:
        """Different-length horizontal rules are inconsistent."""
        content = "Text\n\n----\n\nMore\n\n---\n\nEnd\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 7
        assert "Expected '----'" in violations[0].message
        assert "'---'" in violations[0].message

    def test_underscore_style(self, rule: MD035, config: MD035Config) -> None:
        """Underscore horizontal rules are detected."""
        content = "Text\n\n___\n\nMore\n\n___\n\nEnd\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_underscore_vs_dash(self, rule: MD035, config: MD035Config) -> None:
        """Underscore and dash horizontal rules are inconsistent."""
        content = "Text\n\n---\n\nMore\n\n___\n\nEnd\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 7
        assert "Expected '---'" in violations[0].message
        assert "'___'" in violations[0].message

    def test_column_position(self, rule: MD035, config: MD035Config) -> None:
        """Violations report column 1."""
        content = "Text\n\n---\n\n***\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].column == 1

    def test_context_contains_rule(self, rule: MD035, config: MD035Config) -> None:
        """Violation context contains the horizontal rule."""
        content = "Text\n\n---\n\n***\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].context == "***"

    def test_fix_returns_none_for_valid(self, rule: MD035, config: MD035Config) -> None:
        """Fixing valid document returns None."""
        content = load_fixture("md035", "valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_corrects_invalid(self, rule: MD035, config: MD035Config) -> None:
        """Fixing invalid document normalizes horizontal rules."""
        content = load_fixture("md035", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []
        # The second HR (***) should become ---
        assert "***" not in result
        assert result.count("---") == 2

    def test_fix_multiple_inconsistent(self, rule: MD035, config: MD035Config) -> None:
        """Fix normalizes multiple inconsistent rules to the first style."""
        content = "Text\n\n---\n\nMore\n\n***\n\nEven more\n\n- - -\n\nEnd\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_specific_style(self, rule: MD035) -> None:
        """Fix with specific style replaces non-matching rules."""
        config = MD035Config(style="***")
        content = "Text\n\n---\n\nMore\n\n***\n\nEnd\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []
        assert "---" not in result

    def test_fix_no_horizontal_rules(self, rule: MD035, config: MD035Config) -> None:
        """Fix returns None when there are no horizontal rules."""
        content = "# Heading\n\nSome text.\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_single_horizontal_rule(self, rule: MD035, config: MD035Config) -> None:
        """Fix returns None for a single horizontal rule."""
        content = "# Heading\n\n---\n\nSome text.\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_preserves_leading_whitespace(self, rule: MD035, config: MD035Config) -> None:
        """Fix preserves leading whitespace on horizontal rules."""
        content = "Text\n\n   ---\n\nMore\n\n   ***\n\nEnd\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert "   ---" in result
        assert "   ***" not in result
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []
