from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md042 import MD042, MD042Config
from tests.conftest import load_fixture


class TestMD042:
    @pytest.fixture
    def rule(self) -> MD042:
        return MD042()

    @pytest.fixture
    def config(self) -> MD042Config:
        return MD042Config()

    def test_valid_document(self, rule: MD042, config: MD042Config) -> None:
        """Valid document with proper links passes the rule."""
        content = load_fixture("md042", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD042, config: MD042Config) -> None:
        """Invalid document with empty links triggers violations."""
        content = load_fixture("md042", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 3
        assert violations[0].rule_id == "MD042"
        assert violations[0].rule_name == "no-empty-links"

    def test_empty_link_destination(self, rule: MD042, config: MD042Config) -> None:
        """Empty link destination is detected."""
        content = "[empty link]()"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert violations[0].column == 1
        assert "empty" in violations[0].message.lower()

    def test_empty_fragment(self, rule: MD042, config: MD042Config) -> None:
        """Empty fragment link is detected."""
        content = "[empty fragment](#)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert "empty" in violations[0].message.lower()

    def test_whitespace_only_destination(self, rule: MD042, config: MD042Config) -> None:
        """Link with whitespace-only destination is detected."""
        content = "[whitespace link](   )"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_valid_link_not_flagged(self, rule: MD042, config: MD042Config) -> None:
        """Valid links are not flagged."""
        content = "[valid link](https://example.com/)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_valid_fragment_not_flagged(self, rule: MD042, config: MD042Config) -> None:
        """Valid fragment links are not flagged."""
        content = "[section link](#section-name)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_reference_link_empty_definition(self, rule: MD042, config: MD042Config) -> None:
        """Reference link with empty definition is detected."""
        content = """\
[reference link][ref]

[ref]: #
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_reference_link_valid_definition(self, rule: MD042, config: MD042Config) -> None:
        """Reference link with valid definition is not flagged."""
        content = """\
[reference link][ref]

[ref]: https://example.com/
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_collapsed_reference_empty(self, rule: MD042, config: MD042Config) -> None:
        """Collapsed reference link with empty definition is detected."""
        content = """\
[collapsed][]

[collapsed]: #
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_shortcut_reference_empty(self, rule: MD042, config: MD042Config) -> None:
        """Shortcut reference link with empty definition is detected."""
        content = """\
[shortcut]

[shortcut]: #
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_code_blocks_ignored(self, rule: MD042, config: MD042Config) -> None:
        """Links in code blocks are ignored."""
        content = """\
```
[empty link]()
```
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_inline_code_ignored(self, rule: MD042, config: MD042Config) -> None:
        """Links in inline code are ignored."""
        content = "Use `[empty]()` for example."
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_empty_links(self, rule: MD042, config: MD042Config) -> None:
        """Multiple empty links on same line are detected."""
        content = "[first]() and [second](#)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2

    def test_empty_document(self, rule: MD042, config: MD042Config) -> None:
        """Empty document has no violations."""
        content = ""
        doc = Document(Path("empty.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_column_position_reported(self, rule: MD042, config: MD042Config) -> None:
        """Column position is correctly reported."""
        content = "Some text [empty]() more text"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 1
        assert violations[0].column == 11  # Position of the opening bracket

    def test_context_includes_line_content(self, rule: MD042, config: MD042Config) -> None:
        """Violation context includes the full line content."""
        content = "Bad link: [empty]()"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].context == content

    def test_image_not_flagged(self, rule: MD042, config: MD042Config) -> None:
        """Empty image syntax is not flagged as an empty link."""
        content = "![alt text]()"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_image_with_url_not_flagged(self, rule: MD042, config: MD042Config) -> None:
        """Image with valid URL is not flagged."""
        content = "![alt text](https://example.com/img.png)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_angle_bracket_empty_destination(self, rule: MD042, config: MD042Config) -> None:
        """Link with empty angle bracket destination is detected."""
        content = "[text](<>)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_angle_bracket_hash_destination(self, rule: MD042, config: MD042Config) -> None:
        """Link with angle bracket hash destination is detected."""
        content = "[text](<#>)"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_empty_reference_definition(self, rule: MD042, config: MD042Config) -> None:
        """Reference with truly empty definition is not resolved as a link."""
        content = """\
[ref]

[ref]:
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0
