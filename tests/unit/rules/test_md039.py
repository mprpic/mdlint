from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md039 import MD039, MD039Config
from tests.conftest import load_fixture


class TestMD039:
    @pytest.fixture
    def rule(self) -> MD039:
        return MD039()

    @pytest.fixture
    def config(self) -> MD039Config:
        return MD039Config()

    def test_valid_document(self, rule: MD039, config: MD039Config) -> None:
        """Valid document with properly formatted links passes the rule."""
        content = load_fixture("md039", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD039, config: MD039Config) -> None:
        """Invalid document with spaces in link text triggers violations."""
        content = load_fixture("md039", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 4  # Leading, trailing, and both sides (counts as 2)
        assert violations[0].rule_id == "MD039"
        assert violations[0].rule_name == "no-space-in-links"

    def test_leading_space_detection(self, rule: MD039, config: MD039Config) -> None:
        """Leading space in link text is detected."""
        content = "[ link with leading space](https://example.com/)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert violations[0].column == 1
        assert "leading" in violations[0].message.lower()

    def test_trailing_space_detection(self, rule: MD039, config: MD039Config) -> None:
        """Trailing space in link text is detected."""
        content = "[link with trailing space ](https://example.com/)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert violations[0].column == 1
        assert "trailing" in violations[0].message.lower()

    def test_both_sides_spaces_detected(self, rule: MD039, config: MD039Config) -> None:
        """Spaces on both sides of link text are detected as two violations."""
        content = "[ spaces on both sides ](https://example.com/)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        # Both violations should be on the same line
        assert violations[0].line == 1
        assert violations[1].line == 1

    def test_column_position_reported(self, rule: MD039, config: MD039Config) -> None:
        """Column position is correctly reported."""
        content = "Some text [ link](https://example.com/) more text"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert violations[0].column == 11  # Position of the opening bracket

    def test_multiple_links_on_same_line(self, rule: MD039, config: MD039Config) -> None:
        """Multiple problematic links on the same line are reported."""
        content = "[ first ](https://first.com/) and [ second ](https://second.com/)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        # 4 violations: 2 per link (leading + trailing)
        assert len(violations) == 4

    def test_code_blocks_ignored(self, rule: MD039, config: MD039Config) -> None:
        """Links in code blocks are ignored."""
        content = """\
```
[ link with space ](https://example.com/)
```
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_inline_code_ignored(self, rule: MD039, config: MD039Config) -> None:
        """Links in inline code are ignored."""
        content = "Use `[ link ](url)` for example."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_empty_document(self, rule: MD039, config: MD039Config) -> None:
        """Empty document has no violations."""
        content = ""
        doc = Document(Path("empty.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_context_includes_line_content(self, rule: MD039, config: MD039Config) -> None:
        """Violation context includes the full line content."""
        content = "Bad link: [ text ](https://example.com/)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].context == content

    def test_reference_links_checked(self, rule: MD039, config: MD039Config) -> None:
        """Reference style links are also checked."""
        content = "[ link text ][ref]\n\n[ref]: https://example.com"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2  # Leading and trailing

    def test_image_links_not_checked(self, rule: MD039, config: MD039Config) -> None:
        """Image alt text with spaces is not checked (matches reference implementations)."""
        content = "![ image alt ](image.png)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_no_violation_for_empty_link(self, rule: MD039, config: MD039Config) -> None:
        """Empty link text does not trigger violations."""
        content = "[](https://example.com/)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_spaces_detected(self, rule: MD039, config: MD039Config) -> None:
        """Multiple leading/trailing spaces are detected."""
        content = "[   multiple spaces   ](https://example.com/)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2  # Leading and trailing
