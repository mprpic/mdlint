from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md059 import MD059, MD059Config
from tests.conftest import load_fixture


class TestMD059:
    @pytest.fixture
    def rule(self) -> MD059:
        return MD059()

    @pytest.fixture
    def config(self) -> MD059Config:
        return MD059Config()

    def test_valid_document(self, rule: MD059, config: MD059Config) -> None:
        """Valid document with descriptive links passes the rule."""
        content = load_fixture("md059", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD059, config: MD059Config) -> None:
        """Invalid document with non-descriptive links triggers violations."""
        content = load_fixture("md059", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 4
        assert violations[0].rule_id == "MD059"
        assert violations[0].rule_name == "descriptive-link-text"

    def test_click_here_detected(self, rule: MD059, config: MD059Config) -> None:
        """Link with 'click here' text is detected."""
        content = "[click here](https://example.com/)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert violations[0].column == 1
        assert "click here" in violations[0].message.lower()

    def test_here_detected(self, rule: MD059, config: MD059Config) -> None:
        """Link with 'here' text is detected."""
        content = "[here](https://example.com/)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_link_detected(self, rule: MD059, config: MD059Config) -> None:
        """Link with 'link' text is detected."""
        content = "[link](https://example.com/)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_more_detected(self, rule: MD059, config: MD059Config) -> None:
        """Link with 'more' text is detected."""
        content = "[more](https://example.com/)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_case_insensitive(self, rule: MD059, config: MD059Config) -> None:
        """Detection is case insensitive."""
        content = "[Click Here](https://example.com/)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_descriptive_link_not_flagged(self, rule: MD059, config: MD059Config) -> None:
        """Descriptive link text is not flagged."""
        content = "[Download the budget](https://example.com/budget.pdf)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_code_blocks_ignored(self, rule: MD059, config: MD059Config) -> None:
        """Links in code blocks are ignored."""
        content = """\
```
[click here](https://example.com/)
```
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_inline_code_ignored(self, rule: MD059, config: MD059Config) -> None:
        """Links in inline code are ignored."""
        content = "Use `[click here](url)` for example."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_custom_prohibited_texts(self, rule: MD059) -> None:
        """Custom prohibited_texts configuration is respected."""
        config = MD059Config(prohibited_texts=["foo", "bar"])
        content = "[foo](https://example.com/)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_custom_prohibited_texts_default_allowed(self, rule: MD059) -> None:
        """Custom prohibited_texts does not include defaults."""
        config = MD059Config(prohibited_texts=["foo"])
        content = "[click here](https://example.com/)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_whitespace_normalization(self, rule: MD059, config: MD059Config) -> None:
        """Extra whitespace in link text is normalized."""
        content = "[click   here](https://example.com/)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_punctuation_ignored(self, rule: MD059, config: MD059Config) -> None:
        """Punctuation in link text is ignored during matching."""
        content = "[click here!](https://example.com/)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_multiple_links_on_same_line(self, rule: MD059, config: MD059Config) -> None:
        """Multiple non-descriptive links on same line are detected."""
        content = "[here](url1) and [link](url2)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2

    def test_reference_link_detected(self, rule: MD059, config: MD059Config) -> None:
        """Reference link with non-descriptive text is detected."""
        content = """\
[click here][ref]

[ref]: https://example.com/
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_collapsed_reference_detected(self, rule: MD059, config: MD059Config) -> None:
        """Collapsed reference link with non-descriptive text is detected."""
        content = """\
[here][]

[here]: https://example.com/
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_shortcut_reference_detected(self, rule: MD059, config: MD059Config) -> None:
        """Shortcut reference link with non-descriptive text is detected."""
        content = """\
[link]

[link]: https://example.com/
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_empty_document(self, rule: MD059, config: MD059Config) -> None:
        """Empty document has no violations."""
        content = ""
        doc = Document(Path("empty.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_code_text_in_link_allowed(self, rule: MD059, config: MD059Config) -> None:
        """Link with inline code in text is allowed (even if text matches)."""
        content = "[`here`](https://example.com/)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_html_text_in_link_allowed(self, rule: MD059, config: MD059Config) -> None:
        """Link with HTML in text is allowed (even if text matches)."""
        content = load_fixture("md059", "html_text.md")
        doc = Document(Path("html_text.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_empty_prohibited_texts(self, rule: MD059) -> None:
        """Empty prohibited_texts list produces no violations."""
        config = MD059Config(prohibited_texts=[])
        content = load_fixture("md059", "empty_prohibited.md")
        doc = Document(Path("empty_prohibited.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_empty_link_text(self, rule: MD059, config: MD059Config) -> None:
        """Empty link text is not flagged."""
        content = load_fixture("md059", "empty_link_text.md")
        doc = Document(Path("empty_link_text.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_context_includes_line_content(self, rule: MD059, config: MD059Config) -> None:
        """Violation context includes the full line content."""
        content = "See [here](https://example.com/) for details."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].context == content
