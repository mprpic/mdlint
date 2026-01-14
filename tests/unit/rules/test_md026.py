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
