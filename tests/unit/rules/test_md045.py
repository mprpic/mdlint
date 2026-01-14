from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md045 import MD045, MD045Config
from tests.conftest import load_fixture


class TestMD045:
    @pytest.fixture
    def rule(self) -> MD045:
        return MD045()

    @pytest.fixture
    def config(self) -> MD045Config:
        return MD045Config()

    def test_valid_document(self, rule: MD045, config: MD045Config) -> None:
        """Valid document with images that have alt text passes the rule."""
        content = load_fixture("md045", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD045, config: MD045Config) -> None:
        """Invalid document with images missing alt text triggers violations."""
        content = load_fixture("md045", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 3  # Markdown image, reference image, HTML image
        assert violations[0].rule_id == "MD045"
        assert violations[0].rule_name == "no-alt-text"

    def test_markdown_image_without_alt(self, rule: MD045, config: MD045Config) -> None:
        """Markdown image without alt text is detected."""
        content = "![](image.png)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert violations[0].column == 1

    def test_markdown_image_with_alt(self, rule: MD045, config: MD045Config) -> None:
        """Markdown image with alt text passes."""
        content = "![Alt text](image.png)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_reference_image_without_alt(self, rule: MD045, config: MD045Config) -> None:
        """Reference style image without alt text is detected."""
        content = """\
![][ref]

[ref]: image.png
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1

    def test_reference_image_with_alt(self, rule: MD045, config: MD045Config) -> None:
        """Reference style image with alt text passes."""
        content = """\
![Alt text][ref]

[ref]: image.png
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_html_img_without_alt(self, rule: MD045, config: MD045Config) -> None:
        """HTML img tag without alt attribute is detected."""
        content = '<img src="image.png" />'
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert violations[0].column == 1

    def test_html_img_with_alt(self, rule: MD045, config: MD045Config) -> None:
        """HTML img tag with alt attribute passes."""
        content = '<img src="image.png" alt="Alt text" />'
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_html_img_with_empty_alt(self, rule: MD045, config: MD045Config) -> None:
        """HTML img tag with empty alt attribute passes (decorative images)."""
        content = '<img src="decorative.png" alt="" />'
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_html_img_aria_hidden(self, rule: MD045, config: MD045Config) -> None:
        """HTML img tag with aria-hidden=true is allowed without alt."""
        content = '<img src="decorative.png" aria-hidden="true" />'
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_html_img_aria_hidden_case_insensitive(self, rule: MD045, config: MD045Config) -> None:
        """HTML img tag with ARIA-HIDDEN=TRUE (uppercase) is allowed."""
        content = '<img src="decorative.png" ARIA-HIDDEN="TRUE" />'
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_code_blocks_ignored(self, rule: MD045, config: MD045Config) -> None:
        """Images in code blocks are ignored."""
        content = """\
```
![](image.png)
<img src="image.png" />
```
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_inline_code_ignored(self, rule: MD045, config: MD045Config) -> None:
        """Images in inline code are ignored."""
        content = "Use `![](image.png)` for images."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_images_same_line(self, rule: MD045, config: MD045Config) -> None:
        """Multiple images without alt text on same line are reported."""
        content = "![](a.png) ![](b.png)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2

    def test_empty_document(self, rule: MD045, config: MD045Config) -> None:
        """Empty document has no violations."""
        content = ""
        doc = Document(Path("empty.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_context_includes_line_content(self, rule: MD045, config: MD045Config) -> None:
        """Violation context includes the full line content."""
        content = "Missing alt: ![](image.png)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].context == content

    def test_whitespace_only_alt_text(self, rule: MD045, config: MD045Config) -> None:
        """Image with whitespace-only alt text is detected as violation."""
        content = "![   ](image.png)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_html_closing_img_tag_ignored(self, rule: MD045, config: MD045Config) -> None:
        """Closing img tags (if any) should not trigger violations."""
        # Note: img is self-closing but we shouldn't crash on malformed HTML
        content = '<img src="image.png" alt="text">Some content</img>'
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_html_img_with_single_quotes(self, rule: MD045, config: MD045Config) -> None:
        """HTML img tag with single-quoted alt attribute passes."""
        content = "<img src='image.png' alt='Alt text' />"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_html_img_with_unquoted_alt(self, rule: MD045, config: MD045Config) -> None:
        """HTML img tag with unquoted alt attribute passes."""
        content = "<img src=image.png alt=text />"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_html_img_uppercase_tag(self, rule: MD045, config: MD045Config) -> None:
        """HTML IMG tag (uppercase) without alt is detected."""
        content = '<IMG src="image.png" />'
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_column_position_multiple_images(self, rule: MD045, config: MD045Config) -> None:
        """Column position is correctly reported for multiple images."""
        content = "Text ![](a.png) more ![](b.png) end"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].column == 6  # Position of first !
        assert violations[1].column == 22  # Position of second !

    def test_image_in_blockquote(self, rule: MD045, config: MD045Config) -> None:
        """Image without alt text inside a blockquote is detected with correct column."""
        content = "> ![](image.png)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert violations[0].column == 3  # Position of ! after "> "

    def test_image_nested_in_link(self, rule: MD045, config: MD045Config) -> None:
        """Image without alt text nested inside a link is detected."""
        content = "[![](img.png)](url)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].column == 2  # Position of ! after [
