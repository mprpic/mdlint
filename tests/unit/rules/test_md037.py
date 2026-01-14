from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md037 import MD037, MD037Config
from tests.conftest import load_fixture


class TestMD037:
    @pytest.fixture
    def rule(self) -> MD037:
        return MD037()

    @pytest.fixture
    def config(self) -> MD037Config:
        return MD037Config()

    def test_valid_document(self, rule: MD037, config: MD037Config) -> None:
        """Valid document with correct emphasis passes the rule."""
        content = load_fixture("md037", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD037, config: MD037Config) -> None:
        """Invalid document with spaces inside emphasis triggers violations."""
        content = load_fixture("md037", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) > 0
        assert violations[0].rule_id == "MD037"
        assert violations[0].rule_name == "no-space-in-emphasis"

    def test_space_after_opening_asterisks(self, rule: MD037, config: MD037Config) -> None:
        """Space after opening bold asterisks is detected."""
        content = "Text with ** bold** words"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "**" in violations[0].message

    def test_space_before_closing_asterisks(self, rule: MD037, config: MD037Config) -> None:
        """Space before closing bold asterisks is detected."""
        content = "Text with **bold ** words"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_space_both_sides_asterisks(self, rule: MD037, config: MD037Config) -> None:
        """Spaces on both sides of bold asterisks are detected."""
        content = "Text with ** bold ** words"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        # Should report two violations (one for each side)
        assert len(violations) == 2

    def test_single_asterisk_italic(self, rule: MD037, config: MD037Config) -> None:
        """Space inside single asterisks for italic is detected."""
        content = "Text with * italic * words"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2

    def test_underscore_emphasis(self, rule: MD037, config: MD037Config) -> None:
        """Space inside underscore emphasis is detected."""
        content = "Text with _ italic _ words"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2

    def test_double_underscore_bold(self, rule: MD037, config: MD037Config) -> None:
        """Space inside double underscore bold is detected."""
        content = "Text with __ bold __ words"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2

    def test_code_blocks_ignored(self, rule: MD037, config: MD037Config) -> None:
        """Spaces inside emphasis in code blocks are ignored."""
        content = """\
# Heading

```
This ** is not ** emphasis in a code block
```

Regular text here.
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_inline_code_ignored(self, rule: MD037, config: MD037Config) -> None:
        """Spaces inside emphasis in inline code are ignored."""
        content = "Use `** bold **` for emphasis with spaces."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_violations_on_line(self, rule: MD037, config: MD037Config) -> None:
        """Multiple emphasis violations on the same line are reported."""
        content = "Text with ** bold ** and * italic * words"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 4  # Two for bold, two for italic

    def test_empty_document(self, rule: MD037, config: MD037Config) -> None:
        """Empty document has no violations."""
        content = ""
        doc = Document(Path("empty.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_proper_emphasis_no_violations(self, rule: MD037, config: MD037Config) -> None:
        """Properly formatted emphasis without spaces passes."""
        content = "This **bold** and *italic* text is correct."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_column_position_reported(self, rule: MD037, config: MD037Config) -> None:
        """Column position is correctly reported."""
        content = "Text ** bold ** here"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) >= 1
        # First violation should be at the opening **
        assert violations[0].column > 0

    def test_context_includes_line_content(self, rule: MD037, config: MD037Config) -> None:
        """Violation context includes the full line content."""
        content = "Bad emphasis: ** bold **"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) >= 1
        assert violations[0].context == content

    def test_triple_asterisks_bold_italic(self, rule: MD037, config: MD037Config) -> None:
        """Spaces inside triple asterisks (bold+italic) are detected."""
        content = "Text with *** bold italic *** words"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2

    def test_standalone_asterisks_not_flagged(self, rule: MD037, config: MD037Config) -> None:
        """Standalone asterisks without matching pairs are not flagged."""
        # Using a single asterisk without any matching pair
        content = "Use * for bullets. That's it."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_unrelated_asterisks_not_matched(self, rule: MD037, config: MD037Config) -> None:
        """Asterisks from different contexts should not be matched together."""
        # Two separate emphasis uses on the same line (properly formatted)
        content = "The **bold** text and *italic* text"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_escaped_markers_not_flagged(self, rule: MD037, config: MD037Config) -> None:
        """Escaped emphasis markers are not flagged."""
        content = r"\*\* bla \*\*"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_html_block_not_flagged(self, rule: MD037, config: MD037Config) -> None:
        """HTML block content with asterisks is not flagged."""
        content = "<pre>/* test */</pre>"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_html_attributes_not_flagged(self, rule: MD037, config: MD037Config) -> None:
        """HTML attributes containing emphasis-like patterns are not flagged."""
        content = '<div data-value="** test **">'
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_mismatched_marker_lengths_not_flagged(self, rule: MD037, config: MD037Config) -> None:
        """Mismatched marker lengths are not flagged as emphasis."""
        content = "* text ** other"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0
