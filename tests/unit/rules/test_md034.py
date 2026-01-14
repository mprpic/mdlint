from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md034 import MD034, MD034Config
from tests.conftest import load_fixture


class TestMD034:
    @pytest.fixture
    def rule(self) -> MD034:
        return MD034()

    @pytest.fixture
    def config(self) -> MD034Config:
        return MD034Config()

    def test_valid_document(self, rule: MD034, config: MD034Config) -> None:
        """Valid document with properly formatted URLs passes the rule."""
        content = load_fixture("md034", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD034, config: MD034Config) -> None:
        """Invalid document with bare URLs triggers violations."""
        content = load_fixture("md034", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD034"
        assert violations[0].rule_name == "no-bare-urls"

    def test_bare_http_url(self, rule: MD034, config: MD034Config) -> None:
        """Bare HTTP URL is detected."""
        content = "Visit http://example.com/ for more info."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert "http://example.com/" in violations[0].message

    def test_bare_https_url(self, rule: MD034, config: MD034Config) -> None:
        """Bare HTTPS URL is detected."""
        content = "Visit https://example.com/ for more info."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1

    def test_bare_email(self, rule: MD034, config: MD034Config) -> None:
        """Bare email address is detected."""
        content = "Contact user@example.com for help."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert "user@example.com" in violations[0].message

    def test_url_in_angle_brackets(self, rule: MD034, config: MD034Config) -> None:
        """URL in angle brackets is valid."""
        content = "Visit <https://example.com/> for more info."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_email_in_angle_brackets(self, rule: MD034, config: MD034Config) -> None:
        """Email in angle brackets is valid."""
        content = "Contact <user@example.com> for help."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_url_in_link_syntax(self, rule: MD034, config: MD034Config) -> None:
        """URL in markdown link syntax is valid."""
        content = "Visit [example](https://example.com/) for more info."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_url_in_image_syntax(self, rule: MD034, config: MD034Config) -> None:
        """URL in image syntax is valid."""
        content = "![alt text](https://example.com/image.png)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_url_in_inline_code(self, rule: MD034, config: MD034Config) -> None:
        """URL in inline code is valid."""
        content = "Use `https://example.com/` in your config."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_url_in_code_block(self, rule: MD034, config: MD034Config) -> None:
        """URL in fenced code block is valid."""
        content = """\
```
https://example.com/
```
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_url_in_indented_code_block(self, rule: MD034, config: MD034Config) -> None:
        """URL in indented code block is valid."""
        content = """\
Some text:

    https://example.com/
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_bare_urls(self, rule: MD034, config: MD034Config) -> None:
        """Multiple bare URLs on the same line are detected."""
        content = "Check https://one.com/ and https://two.com/ for info."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2

    def test_column_position(self, rule: MD034, config: MD034Config) -> None:
        """Column position is correctly reported."""
        content = "Visit https://example.com/ today."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].column == 7  # "Visit " is 6 chars, URL starts at 7

    def test_empty_document(self, rule: MD034, config: MD034Config) -> None:
        """Empty document has no violations."""
        content = ""
        doc = Document(Path("empty.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_context_includes_line_content(self, rule: MD034, config: MD034Config) -> None:
        """Violation context includes the full line content."""
        content = "Bare URL: https://example.com/"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].context == content

    def test_reference_definition_excluded(self, rule: MD034, config: MD034Config) -> None:
        """URL in reference link definition is valid."""
        content = "[example]: https://example.com/"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_shortcut_link_excluded(self, rule: MD034, config: MD034Config) -> None:
        """Shortcut link syntax with URL is valid."""
        content = "[https://example.com/]"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_ftp_url(self, rule: MD034, config: MD034Config) -> None:
        """Bare FTP URL is detected."""
        content = "Download from ftp://files.example.com/file.zip today."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "ftp://files.example.com/file.zip" in violations[0].message

    def test_url_in_html_attribute(self, rule: MD034, config: MD034Config) -> None:
        """URL inside HTML tag attribute is not flagged."""
        content = '<a href="https://example.com">link</a>'
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_url_in_html_img_src(self, rule: MD034, config: MD034Config) -> None:
        """URL inside HTML img src attribute is not flagged."""
        content = '<img src="https://example.com/img.png" alt="photo">'
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_url_between_html_tags(self, rule: MD034, config: MD034Config) -> None:
        """Bare URL between HTML tags is still flagged."""
        content = "<b>https://example.com</b>"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_trailing_period_stripped(self, rule: MD034, config: MD034Config) -> None:
        """Trailing period is stripped from URL in violation message."""
        content = "Visit https://example.com."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].message == "Bare URL used: https://example.com"

    def test_trailing_comma_stripped(self, rule: MD034, config: MD034Config) -> None:
        """Trailing comma is stripped from URL in violation message."""
        content = "See https://example.com, then continue."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].message == "Bare URL used: https://example.com"

    def test_trailing_semicolon_stripped(self, rule: MD034, config: MD034Config) -> None:
        """Trailing semicolon is stripped from URL in violation message."""
        content = "Link: https://example.com;"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].message == "Bare URL used: https://example.com"

    def test_url_with_balanced_parentheses(self, rule: MD034, config: MD034Config) -> None:
        """URL with balanced parentheses is fully captured."""
        content = "See https://en.wikipedia.org/wiki/Markdown_(markup) for info."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "https://en.wikipedia.org/wiki/Markdown_(markup)" in violations[0].message

    def test_url_with_path_no_trailing_paren(self, rule: MD034, config: MD034Config) -> None:
        """URL without parentheses in path is not affected."""
        content = "Visit https://example.com/path/to/page for info."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "https://example.com/path/to/page" in violations[0].message

    def test_email_with_plus(self, rule: MD034, config: MD034Config) -> None:
        """Email with plus addressing is detected."""
        content = "Contact user+tag@example.com for help."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "user+tag@example.com" in violations[0].message
