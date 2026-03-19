from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md051 import MD051, MD051Config
from tests.conftest import load_fixture


class TestMD051:
    @pytest.fixture
    def rule(self) -> MD051:
        return MD051()

    @pytest.fixture
    def config(self) -> MD051Config:
        return MD051Config()

    def test_valid_document(self, rule: MD051, config: MD051Config) -> None:
        """Valid document with correct link fragments passes the rule."""
        content = load_fixture("md051", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD051, config: MD051Config) -> None:
        """Invalid document with broken link fragments triggers violations."""
        content = load_fixture("md051", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD051"
        assert violations[0].rule_name == "link-fragments"

    def test_valid_fragment_link(self, rule: MD051, config: MD051Config) -> None:
        """Valid fragment link to existing heading passes."""
        content = """\
# My Heading

[Link](#my-heading)
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_fragment_link(self, rule: MD051, config: MD051Config) -> None:
        """Invalid fragment link to non-existent heading is detected."""
        content = """\
# My Heading

[Link](#non-existent)
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3
        assert "#non-existent" in violations[0].message

    def test_top_fragment_always_valid(self, rule: MD051, config: MD051Config) -> None:
        """The #top fragment is always valid."""
        content = """\
# Heading

[Back to top](#top)
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_case_sensitivity(self, rule: MD051, config: MD051Config) -> None:
        """Fragment links are case sensitive by default."""
        content = """\
# My Heading

[Link](#My-Heading)
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        # Should fail because GitHub algorithm converts to lowercase
        assert len(violations) == 1
        assert "Expected: #my-heading" in violations[0].message

    def test_ignore_case_config(self, rule: MD051) -> None:
        """With ignore_case=True, case differences are ignored."""
        config = MD051Config(ignore_case=True)
        content = """\
# My Heading

[Link](#My-Heading)
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_html_id_anchor(self, rule: MD051, config: MD051Config) -> None:
        """HTML elements with id attribute create valid anchors."""
        content = """\
<div id="custom-anchor"></div>

[Link](#custom-anchor)
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_html_a_name_anchor(self, rule: MD051, config: MD051Config) -> None:
        """HTML <a> elements with name attribute create valid anchors."""
        content = """\
<a name="bookmark"></a>

[Link](#bookmark)
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_custom_anchor_in_heading(self, rule: MD051, config: MD051Config) -> None:
        """Custom anchor syntax {#custom-name} in headings is recognized."""
        content = """\
# Heading Name {#custom-name}

[Link](#custom-name)
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_duplicate_headings(self, rule: MD051, config: MD051Config) -> None:
        """Duplicate headings get numbered fragments."""
        content = """\
# Heading

## Heading

[First](#heading)
[Second](#heading-1)
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_heading_with_punctuation(self, rule: MD051, config: MD051Config) -> None:
        """Punctuation is removed from heading fragments."""
        content = """\
# Hello, World!

[Link](#hello-world)
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_heading_with_special_chars(self, rule: MD051, config: MD051Config) -> None:
        """Special characters in headings are handled correctly."""
        content = """\
# What's New?

[Link](#whats-new)
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_heading_with_nbsp(self, rule: MD051, config: MD051Config) -> None:
        """Non-breaking space in heading is treated as a regular space."""
        content = "# Data\u00a0wrangling\n\n[Link](#data-wrangling)\n"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_external_link_ignored(self, rule: MD051, config: MD051Config) -> None:
        """External links (not starting with #) are ignored."""
        content = """\
# Heading

[External](https://example.com)
[Path](/path/to/file)
[Relative](./other.md#section)
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_github_line_fragment(self, rule: MD051, config: MD051Config) -> None:
        """GitHub line fragment syntax is valid."""
        content = """\
# Heading

[Line 20](#L20)
[Lines 19-21](#L19C5-L21C11)
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_ignored_pattern(self, rule: MD051) -> None:
        """Fragments matching ignored_pattern are not checked."""
        config = MD051Config(ignored_pattern=r"^figure-")
        content = """\
# Heading

[Figure 1](#figure-1)
[Figure 2](#figure-2)
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_code_block_ignored(self, rule: MD051, config: MD051Config) -> None:
        """Links in code blocks are ignored."""
        content = """\
# Heading

```markdown
[Link](#non-existent)
```
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_inline_code_ignored(self, rule: MD051, config: MD051Config) -> None:
        """Links in inline code are ignored."""
        content = """\
# Heading

Use `[Link](#non-existent)` as an example.
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_reference_link_fragment(self, rule: MD051, config: MD051Config) -> None:
        """Reference links with fragment destinations are checked."""
        content = """\
# Heading

[Link][ref]

[ref]: #non-existent
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_setext_heading(self, rule: MD051, config: MD051Config) -> None:
        """Setext-style headings create valid anchors."""
        content = """\
Heading One
===========

[Link](#heading-one)
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_empty_document(self, rule: MD051, config: MD051Config) -> None:
        """Empty document has no violations."""
        content = ""
        doc = Document(Path("empty.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_column_position_reported(self, rule: MD051, config: MD051Config) -> None:
        """Column position is correctly reported."""
        content = """\
# Heading

Some text [bad](#missing) more text
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3
        assert violations[0].column == 11

    def test_context_includes_line_content(self, rule: MD051, config: MD051Config) -> None:
        """Violation context includes the full line content."""
        content = """\
# Heading

Bad link: [test](#missing)
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].context == "Bad link: [test](#missing)"

    def test_heading_with_link(self, rule: MD051, config: MD051Config) -> None:
        """Heading containing a link produces correct fragment (link text only)."""
        content = """\
## Heading with [a link](http://example.com)

[link](#heading-with-a-link)
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_heading_with_image(self, rule: MD051, config: MD051Config) -> None:
        """Heading containing an image excludes alt text from fragment."""
        content = """\
## Heading with ![alt](img.png)

[link](#heading-with)
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_heading_with_emphasis(self, rule: MD051, config: MD051Config) -> None:
        """Heading containing emphasis produces correct fragment."""
        content = """\
## The *important* heading

[link](#the-important-heading)
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_reference_def_in_code_block(self, rule: MD051, config: MD051Config) -> None:
        """Reference definitions inside code blocks are not checked."""
        content = """\
# Heading

```
[ref]: #non-existent
```
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_html_anchor_in_code_block(self, rule: MD051, config: MD051Config) -> None:
        """HTML anchors inside code blocks are not valid targets."""
        content = """\
```
<div id="fake-anchor"></div>
```

[link](#fake-anchor)
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "#fake-anchor" in violations[0].message


class TestMD051Fix:
    @pytest.fixture
    def rule(self) -> MD051:
        return MD051()

    @pytest.fixture
    def config(self) -> MD051Config:
        return MD051Config()

    def test_fix_returns_none_for_valid(self, rule: MD051, config: MD051Config) -> None:
        """Fixing already-valid content returns None."""
        content = load_fixture("md051", "valid.md")
        doc = Document(Path("test.md"), content)

        result = rule.fix(doc, config)

        assert result is None

    def test_fix_case_mismatch(self, rule: MD051, config: MD051Config) -> None:
        """Fix corrects case-mismatched link fragments."""
        content = """\
# My Heading

[Link](#My-Heading)
"""
        doc = Document(Path("test.md"), content)

        result = rule.fix(doc, config)

        assert result is not None
        assert "[Link](#my-heading)" in result
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_leaves_nonexistent_fragments(self, rule: MD051, config: MD051Config) -> None:
        """Fix does not change non-existent fragment links."""
        content = load_fixture("md051", "invalid.md")
        doc = Document(Path("test.md"), content)

        result = rule.fix(doc, config)

        assert result is None

    def test_fix_multiple_case_mismatches(self, rule: MD051, config: MD051Config) -> None:
        """Fix corrects multiple case-mismatched fragments."""
        content = """\
# First Heading

## Second Heading

[Link 1](#First-Heading)
[Link 2](#Second-Heading)
"""
        doc = Document(Path("test.md"), content)

        result = rule.fix(doc, config)

        assert result is not None
        assert "[Link 1](#first-heading)" in result
        assert "[Link 2](#second-heading)" in result
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_reference_definition_case_mismatch(self, rule: MD051, config: MD051Config) -> None:
        """Fix corrects case-mismatched reference definition fragments."""
        content = """\
# Heading

[Link][ref]

[ref]: #Heading
"""
        doc = Document(Path("test.md"), content)

        result = rule.fix(doc, config)

        assert result is not None
        assert "[ref]: #heading" in result
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_skips_code_blocks(self, rule: MD051, config: MD051Config) -> None:
        """Fix does not modify links inside code blocks."""
        content = """\
# Heading

```markdown
[Link](#Heading)
```
"""
        doc = Document(Path("test.md"), content)

        result = rule.fix(doc, config)

        assert result is None

    def test_fix_skips_inline_code(self, rule: MD051, config: MD051Config) -> None:
        """Fix does not modify links inside inline code spans."""
        content = """\
# Heading

Use `[Link](#Heading)` as example.
"""
        doc = Document(Path("test.md"), content)

        result = rule.fix(doc, config)

        assert result is None

    def test_fix_mixed_valid_and_case_mismatch(self, rule: MD051, config: MD051Config) -> None:
        """Fix only corrects case mismatches, leaving valid and non-existent links alone."""
        content = """\
# Heading

[Valid](#heading)
[Case mismatch](#Heading)
[Non-existent](#missing)
"""
        doc = Document(Path("test.md"), content)

        result = rule.fix(doc, config)

        assert result is not None
        assert "[Valid](#heading)" in result
        assert "[Case mismatch](#heading)" in result
        assert "[Non-existent](#missing)" in result
