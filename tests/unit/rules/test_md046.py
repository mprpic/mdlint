from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md046 import MD046, MD046Config
from tests.conftest import load_fixture


class TestMD046:
    @pytest.fixture
    def rule(self) -> MD046:
        return MD046()

    @pytest.fixture
    def config(self) -> MD046Config:
        return MD046Config()

    def test_valid_fenced_default(self, rule: MD046, config: MD046Config) -> None:
        """Valid document with all fenced code blocks (default style)."""
        content = load_fixture("md046", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_mixed_styles(self, rule: MD046, config: MD046Config) -> None:
        """Invalid document with mixed code block styles (default fenced style)."""
        content = load_fixture("md046", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD046"
        assert violations[0].line == 12
        assert violations[0].column == 1
        assert "expected fenced" in violations[0].message
        assert "found indented" in violations[0].message

    def test_no_code_blocks(self, rule: MD046, config: MD046Config) -> None:
        """Document without code blocks."""
        content = load_fixture("md046", "no_code.md")
        doc = Document(Path("no_code.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_config_fenced_style(self, rule: MD046) -> None:
        """Enforce fenced style via config."""
        config = MD046Config(style="fenced")
        content = load_fixture("md046", "fenced_only.md")
        doc = Document(Path("fenced_only.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_config_fenced_style_violation(self, rule: MD046) -> None:
        """Fenced style config with indented code block."""
        config = MD046Config(style="fenced")
        content = load_fixture("md046", "indented_only.md")
        doc = Document(Path("indented_only.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert "expected fenced" in violations[0].message

    def test_config_indented_style(self, rule: MD046) -> None:
        """Enforce indented style via config."""
        config = MD046Config(style="indented")
        content = load_fixture("md046", "indented_only.md")
        doc = Document(Path("indented_only.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_config_indented_style_valid_fixture(self, rule: MD046) -> None:
        """Enforce indented style against indented_valid fixture."""
        config = MD046Config(style="indented")
        content = load_fixture("md046", "indented_valid.md")
        doc = Document(Path("indented_valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_config_indented_style_violation(self, rule: MD046) -> None:
        """Indented style config with fenced code block."""
        config = MD046Config(style="indented")
        content = load_fixture("md046", "fenced_only.md")
        doc = Document(Path("fenced_only.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert "expected indented" in violations[0].message

    def test_consistent_mode_fenced_first(self, rule: MD046) -> None:
        """Consistent mode with fenced first."""
        config = MD046Config(style="consistent")
        content = load_fixture("md046", "fenced_only.md")
        doc = Document(Path("fenced_only.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_consistent_mode_indented_first(self, rule: MD046) -> None:
        """Consistent mode with indented first."""
        config = MD046Config(style="consistent")
        content = load_fixture("md046", "indented_only.md")
        doc = Document(Path("indented_only.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_consistent_mode_indented_first_with_violation(self, rule: MD046) -> None:
        """Consistent mode starting with indented, then fenced."""
        config = MD046Config(style="consistent")
        content = load_fixture("md046", "indented_then_fenced.md")
        doc = Document(Path("indented_then_fenced.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD046"
        assert violations[0].line == 7
        assert "expected indented" in violations[0].message
        assert "found fenced" in violations[0].message

    def test_consistent_mode_mixed_styles(self, rule: MD046) -> None:
        """Consistent mode with mixed styles reports violations."""
        config = MD046Config(style="consistent")
        content = load_fixture("md046", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "expected fenced" in violations[0].message

    def test_fenced_code_block_in_list(self, rule: MD046) -> None:
        """Fenced code block inside a list item should not trigger false positive."""
        config = MD046Config(style="consistent")
        content = load_fixture("md046", "fenced_in_list.md")
        doc = Document(Path("fenced_in_list.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0


class TestMD046Fix:
    @pytest.fixture
    def rule(self) -> MD046:
        return MD046()

    @pytest.fixture
    def config(self) -> MD046Config:
        return MD046Config()

    def test_fix_converts_indented_to_fenced(self, rule: MD046, config: MD046Config) -> None:
        """Fix converts indented code blocks to fenced (default style)."""
        content = load_fixture("md046", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_returns_none_for_valid_fenced(self, rule: MD046, config: MD046Config) -> None:
        """Fix returns None when all code blocks already use fenced style."""
        content = load_fixture("md046", "valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_returns_none_for_no_code_blocks(self, rule: MD046, config: MD046Config) -> None:
        """Fix returns None when there are no code blocks."""
        content = load_fixture("md046", "no_code.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_converts_fenced_to_indented(self, rule: MD046) -> None:
        """Fix converts fenced code blocks to indented style."""
        config = MD046Config(style="indented")
        content = load_fixture("md046", "fenced_only.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_returns_none_for_valid_indented(self, rule: MD046) -> None:
        """Fix returns None when all code blocks already use indented style."""
        config = MD046Config(style="indented")
        content = load_fixture("md046", "indented_only.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_consistent_mode_fenced_first(self, rule: MD046) -> None:
        """Fix in consistent mode converts to match first style (fenced)."""
        config = MD046Config(style="consistent")
        content = load_fixture("md046", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_consistent_mode_indented_first(self, rule: MD046) -> None:
        """Fix in consistent mode converts to match first style (indented)."""
        config = MD046Config(style="consistent")
        content = load_fixture("md046", "indented_then_fenced.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_all_indented_to_fenced(self, rule: MD046, config: MD046Config) -> None:
        """Fix converts all indented blocks when style is fenced."""
        content = load_fixture("md046", "indented_only.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_preserves_code_content(self, rule: MD046, config: MD046Config) -> None:
        """Fix preserves the actual code content when converting."""
        content = "# Test\n\n    print('hello')\n    print('world')\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert "print('hello')" in result
        assert "print('world')" in result

    def test_fix_skips_list_context_fenced_blocks(self, rule: MD046) -> None:
        """Fix skips fenced blocks inside lists when converting to indented."""
        config = MD046Config(style="indented")
        content = load_fixture("md046", "fenced_in_list.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        # Fenced blocks in list context are skipped, nothing to fix
        assert result is None

    def test_fixable_property(self, rule: MD046) -> None:
        """Rule reports as fixable."""
        assert rule.fixable is True
