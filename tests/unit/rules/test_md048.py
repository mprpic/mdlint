from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md048 import MD048, MD048Config
from tests.conftest import load_fixture


class TestMD048:
    @pytest.fixture
    def rule(self) -> MD048:
        return MD048()

    @pytest.fixture
    def config(self) -> MD048Config:
        return MD048Config()

    def test_valid_document(self, rule: MD048, config: MD048Config) -> None:
        """Valid document with consistent backtick code fences."""
        content = load_fixture("md048", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD048, config: MD048Config) -> None:
        """Invalid document with mixed backtick and tilde fences."""
        content = load_fixture("md048", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD048"
        assert violations[0].line == 12
        assert "tilde" in violations[0].message.lower()

    def test_all_tildes_consistent(self, rule: MD048, config: MD048Config) -> None:
        """Document with all tilde fences is consistent."""
        content = load_fixture("md048", "all_tildes.md")
        doc = Document(Path("all_tildes.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_no_fences(self, rule: MD048, config: MD048Config) -> None:
        """Document without code fences passes."""
        content = load_fixture("md048", "no_fences.md")
        doc = Document(Path("no_fences.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_single_fence(self, rule: MD048, config: MD048Config) -> None:
        """Document with single code fence passes."""
        content = load_fixture("md048", "single_fence.md")
        doc = Document(Path("single_fence.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_tilde_then_backtick_consistent(self, rule: MD048, config: MD048Config) -> None:
        """Document starting with tilde expects subsequent fences to be tildes."""
        content = load_fixture("md048", "tilde_then_backtick.md")
        doc = Document(Path("tilde_then_backtick.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 12
        assert "backtick" in violations[0].message.lower()

    def test_multiple_violations(self, rule: MD048, config: MD048Config) -> None:
        """Document with multiple style changes reports each violation."""
        content = load_fixture("md048", "multiple_violations.md")
        doc = Document(Path("multiple_violations.md"), content)

        violations = rule.check(doc, config)

        # First fence (backtick) sets expected style, then two tilde fences violate
        # The final backtick fence matches expected style, so no violation
        assert len(violations) == 2
        assert violations[0].line == 7  # first tilde
        assert violations[1].line == 11  # second tilde

    def test_style_backtick(self, rule: MD048) -> None:
        """Backtick style requires all fences to use backticks."""
        config = MD048Config(style="backtick")
        content = load_fixture("md048", "all_tildes.md")
        doc = Document(Path("all_tildes.md"), content)

        violations = rule.check(doc, config)

        # All tilde fences should be violations
        assert len(violations) == 2
        assert all("tilde" in v.message.lower() for v in violations)

    def test_style_tilde(self, rule: MD048) -> None:
        """Tilde style requires all fences to use tildes."""
        config = MD048Config(style="tilde")
        content = load_fixture("md048", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        # All backtick fences should be violations
        assert len(violations) == 3
        assert all("backtick" in v.message.lower() for v in violations)

    def test_style_backtick_valid(self, rule: MD048) -> None:
        """Backtick style with all backticks passes."""
        config = MD048Config(style="backtick")
        content = load_fixture("md048", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_style_tilde_valid(self, rule: MD048) -> None:
        """Tilde style with all tildes passes."""
        config = MD048Config(style="tilde")
        content = load_fixture("md048", "all_tildes.md")
        doc = Document(Path("all_tildes.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_fix_consistent_backtick_first(self, rule: MD048, config: MD048Config) -> None:
        """Fix converts tildes to backticks when first fence uses backticks."""
        content = load_fixture("md048", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_consistent_tilde_first(self, rule: MD048, config: MD048Config) -> None:
        """Fix converts backticks to tildes when first fence uses tildes."""
        content = load_fixture("md048", "tilde_then_backtick.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert "```" not in result
        assert "~~~" in result
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_multiple_violations(self, rule: MD048, config: MD048Config) -> None:
        """Fix corrects multiple inconsistent fences."""
        content = load_fixture("md048", "multiple_violations.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_returns_none_for_valid(self, rule: MD048, config: MD048Config) -> None:
        """Fix returns None when document is already valid."""
        content = load_fixture("md048", "valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_returns_none_for_no_fences(self, rule: MD048, config: MD048Config) -> None:
        """Fix returns None when document has no fences."""
        content = load_fixture("md048", "no_fences.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_style_backtick(self, rule: MD048) -> None:
        """Fix converts all tildes to backticks when style is backtick."""
        config = MD048Config(style="backtick")
        content = load_fixture("md048", "all_tildes.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert "~~~" not in result
        assert "```" in result
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_style_tilde(self, rule: MD048) -> None:
        """Fix converts all backticks to tildes when style is tilde."""
        config = MD048Config(style="tilde")
        content = load_fixture("md048", "valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert "```" not in result
        assert "~~~" in result
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_style_backtick_already_valid(self, rule: MD048) -> None:
        """Fix returns None when all fences already use backticks."""
        config = MD048Config(style="backtick")
        content = load_fixture("md048", "valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_style_tilde_already_valid(self, rule: MD048) -> None:
        """Fix returns None when all fences already use tildes."""
        config = MD048Config(style="tilde")
        content = load_fixture("md048", "all_tildes.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None
