from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md048 import MD048, MD048Config
from tests.conftest import load_fixture


def apply_fix(rule: MD048, content: str, config: MD048Config) -> str:
    result = rule.fix(Document(Path("test.md"), content), config)
    return content if result is None else result


def fence_contents(content: str) -> list[str]:
    return [t.content for t in Document(Path("test.md"), content).tokens if t.type == "fence"]


def assert_safe_fix(rule: MD048, content: str, config: MD048Config) -> str:
    """Fix the content, checking the code survives intact and a second fix changes nothing."""
    fixed = apply_fix(rule, content, config)
    assert fence_contents(fixed) == fence_contents(content)
    assert apply_fix(rule, fixed, config) == fixed
    return fixed


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

    def test_fix_lengthens_fence_around_backtick_lines(
        self, rule: MD048, config: MD048Config
    ) -> None:
        """A backtick fence line inside the code would close a same-length new fence."""
        content = load_fixture("md048", "tilde_with_backticks.md")
        result = assert_safe_fix(rule, content, config)
        assert "\n````markdown\n```\ninner\n```\n````\n" in result
        assert rule.check(Document(Path("test.md"), result), config) == []

    def test_fix_blockquote_fence(self, rule: MD048, config: MD048Config) -> None:
        """Fences inside blockquotes are converted with their markers kept."""
        content = load_fixture("md048", "blockquote_fence.md")
        result = assert_safe_fix(rule, content, config)
        assert "\n> ```\n> y\n> ```\n" in result
        assert "\n  > ```\n  > z\n  > ```\n" in result
        assert rule.check(Document(Path("test.md"), result), config) == []

    def test_fix_closing_fence_edge_cases(self, rule: MD048, config: MD048Config) -> None:
        """Longer closing fences are converted whole, and unclosed fences only at the top."""
        content = load_fixture("md048", "closing_fence_edge_cases.md")
        result = assert_safe_fix(rule, content, config)
        assert "\n```\nlonger closing fence\n`````\n" in result
        assert result.endswith("\n````\nunclosed fence\n```\n")
        assert rule.check(Document(Path("test.md"), result), config) == []

    def test_fix_declines_backtick_in_info_string(self, rule: MD048, config: MD048Config) -> None:
        """A backtick fence's info string cannot contain backticks, so the fence is kept."""
        content = load_fixture("md048", "backtick_info_string.md")
        doc = Document(Path("test.md"), content)
        assert len(rule.check(doc, config)) == 1
        assert rule.fix(doc, config) is None
