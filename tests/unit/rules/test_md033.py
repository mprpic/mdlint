from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md033 import MD033, MD033Config
from tests.conftest import load_fixture


class TestMD033:
    @pytest.fixture
    def rule(self) -> MD033:
        return MD033()

    @pytest.fixture
    def config(self) -> MD033Config:
        return MD033Config()

    def test_valid_document(self, rule: MD033, config: MD033Config) -> None:
        """Valid document passes the rule."""
        content = load_fixture("md033", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD033, config: MD033Config) -> None:
        """Invalid document triggers violations."""
        content = load_fixture("md033", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        # Only opening tags are flagged, not closing tags
        assert len(violations) == 3
        assert violations[0].rule_id == "MD033"
        assert violations[0].line == 3
        assert "div" in violations[0].message
        assert violations[1].line == 5
        assert "span" in violations[1].message
        assert violations[2].line == 7
        assert "p" in violations[2].message

    def test_allowed_elements(self, rule: MD033) -> None:
        """Allowed elements do not trigger violations."""
        content = load_fixture("md033", "allowed_elements.md")
        doc = Document(Path("allowed_elements.md"), content)
        config = MD033Config(allowed_elements=["br"])

        violations = rule.check(doc, config)

        # Only the div should be flagged, not the br elements
        assert len(violations) == 1
        assert "div" in violations[0].message

    def test_allowed_elements_case_insensitive(self, rule: MD033) -> None:
        """Allowed elements are matched case-insensitively."""
        content = "<BR>Line break"
        doc = Document(Path("test.md"), content)
        config = MD033Config(allowed_elements=["br"])

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_html_block(self, rule: MD033, config: MD033Config) -> None:
        """HTML blocks are detected."""
        content = """\
# Test

<div>
Block HTML
</div>
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) >= 1
        assert violations[0].rule_id == "MD033"

    def test_html_inline(self, rule: MD033, config: MD033Config) -> None:
        """Inline HTML is detected."""
        content = "Text with <strong>inline HTML</strong> inside."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        # Only opening tag is flagged, not closing tag
        assert len(violations) == 1
        assert "strong" in violations[0].message

    def test_self_closing_tags(self, rule: MD033, config: MD033Config) -> None:
        """Self-closing tags are detected."""
        content = "Line break here<br/>more text"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "br" in violations[0].message

    def test_html_in_code_block_ignored(self, rule: MD033, config: MD033Config) -> None:
        """HTML inside code blocks is not flagged."""
        content = """\
# Test

```html
<div>This is in a code block</div>
```
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_html_comments_ignored(self, rule: MD033, config: MD033Config) -> None:
        """HTML comments are not flagged."""
        content = """\
# Test

<!-- This is a comment -->

Some text.
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_allowed_elements(self, rule: MD033) -> None:
        """Multiple allowed elements work correctly."""
        content = """\
<br>
<hr>
<div>Not allowed</div>
"""
        doc = Document(Path("test.md"), content)
        config = MD033Config(allowed_elements=["br", "hr"])

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "div" in violations[0].message

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = MD033Config()

        assert config.allowed_elements == []
        assert config.table_allowed_elements is None

    def test_violation_context(self, rule: MD033, config: MD033Config) -> None:
        """Violations include the line content as context."""
        content = "<div>Inline HTML</div>"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) > 0
        assert violations[0].context == content

    def test_closing_tags_not_reported_separately(self, rule: MD033) -> None:
        """Closing tags are reported for completeness."""
        content = "<div>content</div>"
        doc = Document(Path("test.md"), content)
        config = MD033Config(allowed_elements=["div"])

        violations = rule.check(doc, config)

        # Both opening and closing div tags should be allowed
        assert len(violations) == 0

    def test_multiline_html_comment_ignored(self, rule: MD033, config: MD033Config) -> None:
        """HTML tags inside multi-line and single-line comments are not flagged."""
        content = load_fixture("md033", "multiline_comment.md")
        doc = Document(Path("multiline_comment.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_comment_boundary_tags(self, rule: MD033, config: MD033Config) -> None:
        """Tags on same line as comment boundaries are correctly handled."""
        content = load_fixture("md033", "comment_boundary.md")
        doc = Document(Path("comment_boundary.md"), content)

        violations = rule.check(doc, config)

        # Line 1: <!-- comment --><div>after comment</div> — div flagged at col 17
        # Line 2: <b>before comment</b> <!-- — b flagged at col 1
        # Line 3: <div>not real</div> — inside comment, not flagged
        # Line 4: --> — comment close, not flagged
        # Line 5-6: multi-line comment, not flagged
        # Line 7: --> <span>after multiline close</span> — span flagged
        assert len(violations) == 3
        assert violations[0].line == 1
        assert violations[0].column == 17
        assert "div" in violations[0].message
        assert violations[1].line == 2
        assert violations[1].column == 1
        assert "b" in violations[1].message
        assert violations[2].line == 7
        assert "span" in violations[2].message

    def test_html_in_inline_code_span_ignored(self, rule: MD033, config: MD033Config) -> None:
        """HTML inside inline code spans is not flagged."""
        content = load_fixture("md033", "inline_code.md")
        doc = Document(Path("inline_code.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_tags_on_same_line(self, rule: MD033, config: MD033Config) -> None:
        """Multiple opening tags on the same line are all flagged."""
        content = load_fixture("md033", "multiple_tags.md")
        doc = Document(Path("multiple_tags.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].column == 1
        assert "b" in violations[0].message
        assert violations[1].column == 4
        assert "i" in violations[1].message

    def test_table_allowed_elements(self, rule: MD033) -> None:
        """table_allowed_elements allows specific elements only in tables."""
        content = load_fixture("md033", "table.md")
        doc = Document(Path("table.md"), content)
        config = MD033Config(table_allowed_elements=["br"])

        violations = rule.check(doc, config)

        # In table: br allowed, div not allowed
        # Outside: nothing allowed (allowed_elements is empty)
        assert len(violations) == 3
        assert violations[0].line == 4
        assert "div" in violations[0].message
        assert violations[1].line == 6
        assert "br" in violations[1].message
        assert violations[2].line == 7
        assert "div" in violations[2].message

    def test_table_allowed_elements_defaults_to_allowed(self, rule: MD033) -> None:
        """table_allowed_elements falls back to allowed_elements when not set."""
        content = load_fixture("md033", "table.md")
        doc = Document(Path("table.md"), content)
        config = MD033Config(allowed_elements=["br", "div"])

        violations = rule.check(doc, config)

        # table_allowed_elements is None, so falls back to allowed_elements
        assert len(violations) == 0

    def test_table_allowed_elements_independent_from_allowed(self, rule: MD033) -> None:
        """table_allowed_elements and allowed_elements are independent."""
        content = load_fixture("md033", "table.md")
        doc = Document(Path("table.md"), content)
        config = MD033Config(
            allowed_elements=["div"],
            table_allowed_elements=["br"],
        )

        violations = rule.check(doc, config)

        # In table: br allowed, div not allowed
        # Outside: div allowed, br not allowed
        assert len(violations) == 2
        assert violations[0].line == 4
        assert "div" in violations[0].message
        assert violations[1].line == 6
        assert "br" in violations[1].message
