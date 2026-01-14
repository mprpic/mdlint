from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md022 import MD022, MD022Config
from tests.conftest import load_fixture


class TestMD022:
    @pytest.fixture
    def rule(self) -> MD022:
        return MD022()

    @pytest.fixture
    def config(self) -> MD022Config:
        return MD022Config()

    def test_valid_document(self, rule: MD022, config: MD022Config) -> None:
        """Valid document passes the rule."""
        content = load_fixture("md022", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD022, config: MD022Config) -> None:
        """Invalid document triggers violations."""
        content = load_fixture("md022", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD022"
        # First heading missing blank line below
        assert violations[0].line == 1
        assert "below" in violations[0].message.lower()
        # Second heading missing blank line above
        assert violations[1].line == 5
        assert "above" in violations[1].message.lower()

    def test_no_blank_line_above(self, rule: MD022, config: MD022Config) -> None:
        """Heading without blank line above triggers violation."""
        content = "Some text.\n## Heading\n\nMore text.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 2
        assert "above" in violations[0].message.lower()

    def test_no_blank_line_below(self, rule: MD022, config: MD022Config) -> None:
        """Heading without blank line below triggers violation."""
        content = "# Heading\nSome text.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert "below" in violations[0].message.lower()

    def test_first_heading_no_blank_above_needed(self, rule: MD022, config: MD022Config) -> None:
        """First heading at start of document doesn't need blank line above."""
        content = "# Heading\n\nSome text.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_last_heading_at_end(self, rule: MD022, config: MD022Config) -> None:
        """Last heading at end of document doesn't need blank line below."""
        content = "Some text.\n\n# Heading\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_lines_above_config(self, rule: MD022) -> None:
        """Custom lines_above configuration."""
        config = MD022Config(lines_above=2)
        content = "Some text.\n\n# Heading\n\nMore text.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        # Only 1 blank line above, but 2 required
        assert len(violations) == 1
        assert "above" in violations[0].message.lower()
        assert "2" in violations[0].message

    def test_lines_below_config(self, rule: MD022) -> None:
        """Custom lines_below configuration."""
        config = MD022Config(lines_below=2)
        content = "# Heading\n\nSome text.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        # Only 1 blank line below, but 2 required
        assert len(violations) == 1
        assert "below" in violations[0].message.lower()
        assert "2" in violations[0].message

    def test_lines_above_zero(self, rule: MD022) -> None:
        """lines_above=0 allows no blank lines before headings."""
        config = MD022Config(lines_above=0)
        content = "Some text.\n## Heading\n\nMore text.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_lines_below_zero(self, rule: MD022) -> None:
        """lines_below=0 allows no blank lines after headings."""
        config = MD022Config(lines_below=0)
        content = "# Heading\nSome text.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_headings(self, rule: MD022, config: MD022Config) -> None:
        """Multiple headings all properly spaced."""
        content = "# Heading 1\n\nText.\n\n## Heading 2\n\nMore text.\n\n### Heading 3\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_column_is_one(self, rule: MD022, config: MD022Config) -> None:
        """Column should always be 1 for blank line violations."""
        content = "Some text.\n## Heading\n\nMore text.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].column == 1

    def test_setext_headings_valid(self, rule: MD022, config: MD022Config) -> None:
        """Setext headings with proper blank lines pass."""
        content = load_fixture("md022", "setext_headings.md")
        doc = Document(Path("setext_headings.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_setext_headings_missing_blank_below(self, rule: MD022, config: MD022Config) -> None:
        """Setext heading without blank line below triggers violation."""
        content = load_fixture("md022", "setext_missing_blank.md")
        doc = Document(Path("setext_missing_blank.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert "below" in violations[0].message.lower()

    def test_setext_headings_missing_blank_above(self, rule: MD022, config: MD022Config) -> None:
        """Setext heading without blank line above triggers violation."""
        content = "***\nSetext Heading\n==============\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 2
        assert "above" in violations[0].message.lower()

    def test_extra_blank_lines_accepted(self, rule: MD022, config: MD022Config) -> None:
        """Extra blank lines beyond requirement should not trigger."""
        content = "# Heading 1\n\n\n\nSome text.\n\n\n\n## Heading 2\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_extra_blank_lines_with_higher_requirement(self, rule: MD022) -> None:
        """Extra blank lines beyond custom requirement should not trigger."""
        config = MD022Config(lines_above=2, lines_below=2)
        content = "# Heading 1\n\n\n\nSome text.\n\n\n\n## Heading 2\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_front_matter_requires_blank_line(self, rule: MD022, config: MD022Config) -> None:
        """Heading after front matter requires blank line above."""
        content = "---\ntitle: test\n---\n# Heading\n\nSome text.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "above" in violations[0].message.lower()

    def test_front_matter_with_blank_line(self, rule: MD022, config: MD022Config) -> None:
        """Heading after front matter with blank line passes."""
        content = "---\ntitle: test\n---\n\n# Heading\n\nSome text.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_empty_document(self, rule: MD022, config: MD022Config) -> None:
        """Empty document should produce no violations."""
        content = ""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_consecutive_headings(self, rule: MD022, config: MD022Config) -> None:
        """Blank line between consecutive headings satisfies both requirements."""
        content = "# Heading 1\n\n## Heading 2\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_consecutive_headings_no_blank(self, rule: MD022, config: MD022Config) -> None:
        """Consecutive headings without blank line triggers violation."""
        content = "# Heading 1\n## Heading 2\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert "below" in violations[0].message.lower()
        assert "above" in violations[1].message.lower()

    def test_context_field(self, rule: MD022, config: MD022Config) -> None:
        """Context should contain the heading line."""
        content = "Some text.\n## My Heading\n\nMore text.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert violations[0].context == "## My Heading"

    def test_lines_above_negative_one(self, rule: MD022) -> None:
        """lines_above=-1 disables the above check."""
        config = MD022Config(lines_above=-1)
        content = "Some text.\n## Heading\n\nMore text.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_lines_below_negative_one(self, rule: MD022) -> None:
        """lines_below=-1 disables the below check."""
        config = MD022Config(lines_below=-1)
        content = "# Heading\nSome text.\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0
