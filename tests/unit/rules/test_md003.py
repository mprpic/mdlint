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
