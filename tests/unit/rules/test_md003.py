from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md003 import MD003, MD003Config
from tests.conftest import load_fixture


class TestMD003:
    @pytest.fixture
    def rule(self) -> MD003:
        return MD003()

    @pytest.fixture
    def config(self) -> MD003Config:
        return MD003Config()

    def test_valid_consistent_atx(self, rule: MD003, config: MD003Config) -> None:
        """Valid document with consistent ATX style."""
        content = load_fixture("md003", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_mixed_styles(self, rule: MD003, config: MD003Config) -> None:
        """Invalid document with mixed heading styles."""
        content = load_fixture("md003", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD003"
        assert violations[0].line == 3
        assert violations[0].message == "Expected atx, found setext"

    def test_no_headings(self, rule: MD003, config: MD003Config) -> None:
        """Document without headings."""
        content = load_fixture("md003", "no_headings.md")
        doc = Document(Path("no_headings.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_config_atx_style(self, rule: MD003) -> None:
        """Enforce ATX style via config."""
        config = MD003Config(style="atx")
        content = load_fixture("md003", "atx_style.md")
        doc = Document(Path("atx.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_single_heading(self, rule: MD003, config: MD003Config) -> None:
        """Document with single heading."""
        content = load_fixture("md003", "single_heading.md")
        doc = Document(Path("single.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_config_atx_closed_style(self, rule: MD003) -> None:
        """Enforce ATX closed style via config."""
        config = MD003Config(style="atx_closed")
        content = load_fixture("md003", "atx_closed_style.md")
        doc = Document(Path("atx_closed.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_config_atx_closed_detects_regular_atx(self, rule: MD003) -> None:
        """ATX closed config should flag regular ATX headings."""
        config = MD003Config(style="atx_closed")
        content = load_fixture("md003", "atx_style.md")
        doc = Document(Path("atx.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 3
        assert violations[0].line == 1
        assert violations[0].message == "Expected atx_closed, found atx"
        assert violations[1].line == 3
        assert violations[2].line == 5

    def test_config_setext_style(self, rule: MD003) -> None:
        """Enforce setext style via config."""
        config = MD003Config(style="setext")
        content = load_fixture("md003", "setext_style.md")
        doc = Document(Path("setext.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_config_setext_detects_atx(self, rule: MD003) -> None:
        """Setext config should flag ATX headings."""
        config = MD003Config(style="setext")
        content = load_fixture("md003", "atx_style.md")
        doc = Document(Path("atx.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 3
        assert violations[0].line == 1
        assert violations[0].message == "Expected setext, found atx"
        assert violations[1].line == 3
        assert violations[2].line == 5

    def test_config_setext_detects_atx_closed(self, rule: MD003) -> None:
        """Setext config should flag atx_closed headings."""
        config = MD003Config(style="setext")
        content = load_fixture("md003", "atx_closed_style.md")
        doc = Document(Path("atx_closed.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 3
        assert all(v.message == "Expected setext, found atx_closed" for v in violations)

    def test_config_setext_with_atx_style(self, rule: MD003) -> None:
        """Enforce setext_with_atx style via config."""
        config = MD003Config(style="setext_with_atx")
        content = load_fixture("md003", "setext_with_atx_style.md")
        doc = Document(Path("setext_with_atx.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_config_setext_with_atx_detects_atx_h1(self, rule: MD003) -> None:
        """setext_with_atx config should flag ATX h1/h2 headings."""
        config = MD003Config(style="setext_with_atx")
        content = load_fixture("md003", "setext_with_atx_invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert violations[0].message == "Expected setext, found atx"

    def test_setext_with_atx_allows_atx_for_h3_plus(self, rule: MD003) -> None:
        """setext_with_atx should allow ATX for h3 and above without violations."""
        config = MD003Config(style="setext_with_atx")
        content = load_fixture("md003", "setext_with_atx_style.md")
        doc = Document(Path("setext_with_atx.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_csharp_heading_not_atx_closed(self, rule: MD003, config: MD003Config) -> None:
        """Headings ending with # as content should not be detected as atx_closed."""
        content = load_fixture("md003", "csharp_heading.md")
        doc = Document(Path("csharp.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_csharp_heading_flagged_by_atx_closed_config(self, rule: MD003) -> None:
        """C# heading should be flagged as atx (not atx_closed) when atx_closed is required."""
        config = MD003Config(style="atx_closed")
        content = load_fixture("md003", "csharp_heading.md")
        doc = Document(Path("csharp.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 3
        assert all(v.message == "Expected atx_closed, found atx" for v in violations)

    def test_consistent_setext_first_flags_atx(self, rule: MD003, config: MD003Config) -> None:
        """Consistent mode with setext-first doc should flag ATX headings."""
        content = load_fixture("md003", "setext_first.md")
        doc = Document(Path("setext_first.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 7
        assert violations[0].message == "Expected setext, found atx"

    def test_consistent_atx_closed_first_flags_atx(self, rule: MD003, config: MD003Config) -> None:
        """Consistent mode with atx_closed-first doc should flag regular ATX headings."""
        content = load_fixture("md003", "atx_closed_first.md")
        doc = Document(Path("atx_closed_first.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 5
        assert violations[0].message == "Expected atx_closed, found atx"

    def test_config_setext_with_atx_closed_valid(self, rule: MD003) -> None:
        """Valid setext_with_atx_closed document."""
        config = MD003Config(style="setext_with_atx_closed")
        content = load_fixture("md003", "setext_with_atx_closed_style.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_config_setext_with_atx_closed_invalid(self, rule: MD003) -> None:
        """setext_with_atx_closed should flag ATX h1 and non-closed ATX h3."""
        config = MD003Config(style="setext_with_atx_closed")
        content = load_fixture("md003", "setext_with_atx_closed_invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 1
        assert violations[0].message == "Expected setext, found atx"
        assert violations[1].line == 6
        assert violations[1].message == "Expected atx_closed, found atx"


class TestMD003Fix:
    @pytest.fixture
    def rule(self) -> MD003:
        return MD003()

    @pytest.fixture
    def config(self) -> MD003Config:
        return MD003Config()

    def test_fix_returns_none_for_valid(self, rule: MD003, config: MD003Config) -> None:
        """Valid document should return None (nothing to fix)."""
        content = load_fixture("md003", "valid.md")
        doc = Document(Path("test.md"), content)
        assert rule.fix(doc, config) is None

    def test_fix_returns_none_no_headings(self, rule: MD003, config: MD003Config) -> None:
        """Document with no headings should return None."""
        content = load_fixture("md003", "no_headings.md")
        doc = Document(Path("test.md"), content)
        assert rule.fix(doc, config) is None

    def test_fix_consistent_setext_to_atx(self, rule: MD003, config: MD003Config) -> None:
        """Fix mixed styles in consistent mode (first heading is ATX)."""
        content = load_fixture("md003", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []
        assert "## Setext Heading 2" in result
        assert "----------------" not in result

    def test_fix_consistent_setext_first_skips_unfixable_h3(
        self, rule: MD003, config: MD003Config
    ) -> None:
        """Consistent mode with setext first can't fix h3 (setext only supports h1/h2)."""
        content = load_fixture("md003", "setext_first.md")
        doc = Document(Path("test.md"), content)
        # h3 can't be converted to setext, so nothing can be fixed
        assert rule.fix(doc, config) is None

    def test_fix_consistent_atx_closed_first(self, rule: MD003, config: MD003Config) -> None:
        """Fix mixed styles in consistent mode (first heading is atx_closed)."""
        content = load_fixture("md003", "atx_closed_first.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []
        assert "### Heading 3 ###" in result

    def test_fix_atx_closed_from_atx(self, rule: MD003) -> None:
        """Fix ATX headings to atx_closed style."""
        config = MD003Config(style="atx_closed")
        content = load_fixture("md003", "atx_style.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []
        assert "# ATX H1 #" in result
        assert "## ATX H2 ##" in result
        assert "### ATX H3 ###" in result

    def test_fix_atx_from_atx_closed(self, rule: MD003) -> None:
        """Fix atx_closed headings to ATX style."""
        config = MD003Config(style="atx")
        content = load_fixture("md003", "atx_closed_style.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []
        assert "# ATX Closed Heading 1\n" in result
        assert "## ATX Closed Heading 2\n" in result
        assert "### ATX Closed Heading 3\n" in result

    def test_fix_setext_from_atx(self, rule: MD003) -> None:
        """Fix ATX headings to setext style (h1/h2 only)."""
        config = MD003Config(style="setext")
        content = load_fixture("md003", "atx_style.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert "ATX H1\n======" in result
        assert "ATX H2\n------" in result
        # h3 can't be converted to setext, remains as ATX
        assert "### ATX H3" in result

    def test_fix_atx_from_setext(self, rule: MD003) -> None:
        """Fix setext headings to ATX style."""
        config = MD003Config(style="atx")
        content = load_fixture("md003", "setext_style.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []
        assert "# Setext H1" in result
        assert "## Setext H2" in result
        assert "=========" not in result
        assert "---------" not in result

    def test_fix_setext_with_atx_invalid(self, rule: MD003) -> None:
        """Fix setext_with_atx: h1 should use setext."""
        config = MD003Config(style="setext_with_atx")
        content = load_fixture("md003", "setext_with_atx_invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_setext_with_atx_closed_invalid(self, rule: MD003) -> None:
        """Fix setext_with_atx_closed: h1 to setext, h3 to atx_closed."""
        config = MD003Config(style="setext_with_atx_closed")
        content = load_fixture("md003", "setext_with_atx_closed_invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_returns_none_for_already_valid_atx_closed(self, rule: MD003) -> None:
        """Already valid atx_closed document should return None."""
        config = MD003Config(style="atx_closed")
        content = load_fixture("md003", "atx_closed_style.md")
        doc = Document(Path("test.md"), content)
        assert rule.fix(doc, config) is None

    def test_fix_multiline_setext_to_atx(self, rule: MD003) -> None:
        """All text lines of a setext heading are joined into one ATX heading."""
        config = MD003Config(style="atx")
        content = load_fixture("md003", "setext_multiline.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result == "# Title\n\n## Line one line two\n"
        assert rule.fix(Document(Path("test.md"), result), config) is None

    @pytest.mark.parametrize(
        ("style", "expected"),
        [
            (
                "atx",
                "# Title\n\n> ## Quoted heading\n\n- ## Listed heading\n\n> # Lazy continuation\n",
            ),
            (
                "atx_closed",
                "# Title #\n\n> ## Quoted heading ##\n\n- ## Listed heading ##\n\n"
                "> # Lazy continuation #\n",
            ),
        ],
    )
    def test_fix_setext_in_containers_to_atx(self, rule: MD003, style: str, expected: str) -> None:
        """Converting a quoted or listed setext heading keeps its container prefix."""
        config = MD003Config(style=style)
        content = load_fixture("md003", "setext_in_containers.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result == expected
        assert rule.check(Document(Path("test.md"), result), config) == []
        assert rule.fix(Document(Path("test.md"), result), config) is None

    def test_fix_atx_to_setext_declines_unsafe(self, rule: MD003) -> None:
        """Headings after paragraph or table text, or without text, are reported but kept."""
        config = MD003Config(style="setext")
        content = load_fixture("md003", "atx_to_setext_declines.md")
        doc = Document(Path("test.md"), content)
        assert [v.line for v in rule.check(doc, config)] == [5, 9, 11, 13, 15]
        result = rule.fix(doc, config)
        assert result == (
            "Title\n=====\n\nSome paragraph\n## After Paragraph\n\n| a |\n| - |\n## After Table\n\n"
            "##\n\n> Quoted\n> ------\n\n- Listed\n  ------\n"
        )
        fixed_doc = Document(Path("test.md"), result)
        assert [v.line for v in rule.check(fixed_doc, config)] == [5, 9, 11]
        assert rule.fix(fixed_doc, config) is None

    def test_fixable_property(self, rule: MD003) -> None:
        """Rule should report as fixable."""
        assert rule.fixable is True
