from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md026 import MD026, MD026Config
from tests.conftest import load_fixture


class TestMD026:
    @pytest.fixture
    def rule(self) -> MD026:
        return MD026()

    @pytest.fixture
    def config(self) -> MD026Config:
        return MD026Config()

    def test_valid_document(self, rule: MD026, config: MD026Config) -> None:
        """Valid document passes the rule."""
        content = load_fixture("md026", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD026, config: MD026Config) -> None:
        """Invalid document triggers violations."""
        content = load_fixture("md026", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 3
        assert violations[0].line == 1
        assert violations[0].column == 22
        assert violations[0].rule_id == "MD026"
        assert "." in violations[0].message
        assert violations[1].line == 3
        assert violations[1].column == 22
        assert ":" in violations[1].message
        assert violations[2].line == 5
        assert violations[2].column == 27
        assert ";" in violations[2].message

    def test_question_marks_allowed(self, rule: MD026, config: MD026Config) -> None:
        """Question marks are allowed by default."""
        content = "# Is this a question?\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_custom_punctuation(self, rule: MD026) -> None:
        """Custom punctuation configuration."""
        config = MD026Config(punctuation="?")
        content = "# Is this a question?\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "?" in violations[0].message

    def test_empty_punctuation_disables_rule(self, rule: MD026) -> None:
        """Empty punctuation string disables the rule."""
        config = MD026Config(punctuation="")
        content = "# Heading with period.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_no_headings(self, rule: MD026, config: MD026Config) -> None:
        """Document without headings."""
        content = "Just some text without headings.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_closing_atx_hashes(self, rule: MD026, config: MD026Config) -> None:
        """Closing ATX hashes do not hide trailing punctuation."""
        content = "## Heading with period. ##\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert violations[0].column == 23
        assert "." in violations[0].message

    def test_closing_atx_hashes_no_punctuation(self, rule: MD026, config: MD026Config) -> None:
        """Closing ATX hashes without trailing punctuation pass."""
        content = "## Clean heading ##\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_setext_heading(self, rule: MD026, config: MD026Config) -> None:
        """Setext headings are checked for trailing punctuation."""
        content = "Heading text.\n===\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert violations[0].column == 13
        assert "." in violations[0].message

    def test_setext_heading_valid(self, rule: MD026, config: MD026Config) -> None:
        """Setext headings without trailing punctuation pass."""
        content = "Clean heading\n===\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_html_entity_not_flagged(self, rule: MD026, config: MD026Config) -> None:
        """HTML entity references at end of heading are not flagged."""
        content = "# Heading with &copy;\n\n## Heading with &#169;\n\n### Heading with &#x000A9;\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_html_entity_only_exempts_semicolon(self, rule: MD026, config: MD026Config) -> None:
        """HTML entity exemption only applies to semicolons."""
        content = "# Heading with period.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "." in violations[0].message

    def test_bare_semicolon_still_flagged(self, rule: MD026, config: MD026Config) -> None:
        """A bare trailing semicolon (not an HTML entity) is still flagged."""
        content = "# Heading with semicolon;\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert ";" in violations[0].message

    def test_fix_corrects_invalid(self, rule: MD026, config: MD026Config) -> None:
        """Fix removes trailing punctuation from headings."""
        content = load_fixture("md026", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_returns_none_for_valid(self, rule: MD026, config: MD026Config) -> None:
        """Fix returns None when no violations exist."""
        content = load_fixture("md026", "valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_closing_atx_hashes(self, rule: MD026, config: MD026Config) -> None:
        """Fix removes punctuation before closing ATX hashes."""
        content = "## Heading with period. ##\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result == "## Heading with period ##\n"
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_setext_heading(self, rule: MD026, config: MD026Config) -> None:
        """Fix removes trailing punctuation from setext headings."""
        content = "Heading text.\n===\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result == "Heading text\n===\n"
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_preserves_html_entities(self, rule: MD026, config: MD026Config) -> None:
        """Fix does not remove semicolons from HTML entities."""
        content = "# Heading with &copy;\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_empty_punctuation(self, rule: MD026) -> None:
        """Fix returns None when punctuation config is empty."""
        config = MD026Config(punctuation="")
        content = "# Heading with period.\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_custom_punctuation(self, rule: MD026) -> None:
        """Fix respects custom punctuation configuration."""
        config = MD026Config(punctuation="?")
        content = "# Is this a question?\n"
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result == "# Is this a question\n"
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []
