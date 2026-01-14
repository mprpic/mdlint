from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md043 import MD043, MD043Config
from tests.conftest import load_fixture


class TestMD043:
    @pytest.fixture
    def rule(self) -> MD043:
        return MD043()

    @pytest.fixture
    def config(self) -> MD043Config:
        return MD043Config()

    def test_valid_document(self, rule: MD043) -> None:
        """Valid document passes the rule when headings match required structure."""
        config = MD043Config(headings=["# Document Title", "## Description", "## Examples"])
        content = load_fixture("md043", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD043) -> None:
        """Invalid document triggers violations when headings don't match."""
        config = MD043Config(headings=["# Document Title", "## Description", "## Examples"])
        content = load_fixture("md043", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD043"
        assert violations[0].line == 3
        assert "## Description" in violations[0].message
        assert "## Introduction" in violations[0].message

    def test_empty_headings_config(self, rule: MD043, config: MD043Config) -> None:
        """Empty headings config skips the check."""
        content = load_fixture("md043", "empty_config.md")
        doc = Document(Path("empty_config.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_no_headings_in_document(self, rule: MD043) -> None:
        """Document without headings with required structure configured."""
        config = MD043Config(headings=["# Title"])
        content = load_fixture("md043", "no_headings.md")
        doc = Document(Path("no_headings.md"), content)

        violations = rule.check(doc, config)

        # Should report missing required heading at end of file
        assert len(violations) == 1
        assert "# Title" in violations[0].message

    def test_missing_required_heading(self, rule: MD043) -> None:
        """Document missing a required heading at the end."""
        config = MD043Config(headings=["# Document Title", "## Description", "## Examples"])
        content = load_fixture("md043", "missing_heading.md")
        doc = Document(Path("missing_heading.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "## Examples" in violations[0].message

    def test_wildcard_star_zero_matches(self, rule: MD043) -> None:
        """Star wildcard allows zero unspecified headings."""
        config = MD043Config(headings=["# Document Title", "## Description", "*", "## Examples"])
        content = load_fixture("md043", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_wildcard_star_multiple_matches(self, rule: MD043) -> None:
        """Star wildcard allows multiple unspecified headings."""
        config = MD043Config(headings=["# Document Title", "## Description", "*", "## Footer"])
        content = load_fixture("md043", "wildcard_star.md")
        doc = Document(Path("wildcard_star.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_wildcard_plus_requires_at_least_one(self, rule: MD043) -> None:
        """Plus wildcard requires at least one unspecified heading."""
        config = MD043Config(headings=["# Document Title", "## Introduction", "+", "## Footer"])
        content = load_fixture("md043", "wildcard_plus.md")
        doc = Document(Path("wildcard_plus.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_wildcard_question_matches_one(self, rule: MD043) -> None:
        """Question mark wildcard matches exactly one heading."""
        config = MD043Config(headings=["?", "## Description", "## Examples"])
        content = load_fixture("md043", "wildcard_question.md")
        doc = Document(Path("wildcard_question.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_match_case_sensitive(self, rule: MD043) -> None:
        """With match_case=True, case must match exactly."""
        config = MD043Config(
            headings=["# DOCUMENT TITLE", "## Description", "## Examples"],
            match_case=True,
        )
        content = load_fixture("md043", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1

    def test_match_case_insensitive_default(self, rule: MD043) -> None:
        """With default match_case=False, case is ignored."""
        config = MD043Config(
            headings=["# DOCUMENT TITLE", "## DESCRIPTION", "## EXAMPLES"],
            match_case=False,
        )
        content = load_fixture("md043", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_wildcard_star_at_end(self, rule: MD043) -> None:
        """Star wildcard at end allows extra headings."""
        config = MD043Config(headings=["# Document Title", "*"])
        content = load_fixture("md043", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_extra_headings_without_wildcard(self, rule: MD043) -> None:
        """Extra headings without trailing wildcard cause violations."""
        config = MD043Config(headings=["# Document Title"])
        content = load_fixture("md043", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3

    def test_setext_headings(self, rule: MD043) -> None:
        """Setext-style headings are matched correctly."""
        config = MD043Config(headings=["# Document Title", "## Description", "## Examples"])
        content = load_fixture("md043", "setext_headings.md")
        doc = Document(Path("setext_headings.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_atx_closed_headings(self, rule: MD043) -> None:
        """ATX-closed headings (with trailing #) are matched correctly."""
        config = MD043Config(headings=["# Document Title", "## Description", "## Examples"])
        content = load_fixture("md043", "atx_closed.md")
        doc = Document(Path("atx_closed.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_wildcard_plus_at_end_requires_heading(self, rule: MD043) -> None:
        """Plus wildcard at end requires at least one heading."""
        config = MD043Config(headings=["# Document Title", "+"])
        content = load_fixture("md043", "plus_at_end.md")
        doc = Document(Path("plus_at_end.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "+" in violations[0].message

    def test_wildcard_plus_zero_matches_fails(self, rule: MD043) -> None:
        """Plus wildcard with zero matches between required headings fails."""
        config = MD043Config(headings=["# Document Title", "+", "## Footer"])
        content = load_fixture("md043", "plus_zero_matches.md")
        doc = Document(Path("plus_zero_matches.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "## Footer" in violations[0].message

    def test_wildcard_star_then_required_missing(self, rule: MD043) -> None:
        """Star wildcard followed by required heading with no headings in doc."""
        config = MD043Config(headings=["*", "# Title"])
        content = load_fixture("md043", "star_then_required.md")
        doc = Document(Path("star_then_required.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "*" in violations[0].message

    def test_wildcard_question_at_end_requires_heading(self, rule: MD043) -> None:
        """Question mark wildcard at end requires exactly one heading."""
        config = MD043Config(headings=["# Document Title", "?"])
        content = load_fixture("md043", "question_at_end.md")
        doc = Document(Path("question_at_end.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "?" in violations[0].message

    def test_all_star_no_headings(self, rule: MD043) -> None:
        """All-star config with no headings in document passes."""
        config = MD043Config(headings=["*"])
        content = load_fixture("md043", "all_star_no_headings.md")
        doc = Document(Path("all_star_no_headings.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0
