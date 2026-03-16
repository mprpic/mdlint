from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md053 import MD053, MD053Config
from tests.conftest import load_fixture


class TestMD053:
    @pytest.fixture
    def rule(self) -> MD053:
        return MD053()

    @pytest.fixture
    def config(self) -> MD053Config:
        return MD053Config()

    def test_valid_document(self, rule: MD053, config: MD053Config) -> None:
        """Valid document passes the rule."""
        content = load_fixture("md053", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD053, config: MD053Config) -> None:
        """Invalid document triggers violations."""
        content = load_fixture("md053", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        # Should report unused and duplicate definitions
        assert len(violations) == 2
        assert violations[0].rule_id == "MD053"

    def test_unused_definition(self, rule: MD053, config: MD053Config) -> None:
        """Unused link reference definition triggers violation."""
        content = """\
# Test

Some text.

[unused]: https://example.com
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD053"
        assert violations[0].line == 5
        assert "Unused" in violations[0].message
        assert "unused" in violations[0].message

    def test_duplicate_definition(self, rule: MD053, config: MD053Config) -> None:
        """Duplicate link reference definition triggers violation."""
        content = """\
# Test

A [link][example].

[example]: https://first.example.com
[example]: https://duplicate.example.com
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD053"
        assert violations[0].line == 6
        assert "Duplicate" in violations[0].message

    def test_full_reference_link_used(self, rule: MD053, config: MD053Config) -> None:
        """Full reference link format [text][ref] marks definition as used."""
        content = """\
A [link][example].

[example]: https://example.com
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_collapsed_reference_link_used(self, rule: MD053, config: MD053Config) -> None:
        """Collapsed reference link format [ref][] marks definition as used."""
        content = """\
A [example][].

[example]: https://example.com
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_shortcut_reference_link_used(self, rule: MD053, config: MD053Config) -> None:
        """Shortcut reference link format [ref] marks definition as used."""
        content = """\
A [example].

[example]: https://example.com
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_image_reference_used(self, rule: MD053, config: MD053Config) -> None:
        """Image reference marks definition as used."""
        content = """\
![alt text][image]

[image]: https://example.com/image.png
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_default_ignored_definition(self, rule: MD053, config: MD053Config) -> None:
        """Default ignored definition '//' is not flagged."""
        content = """\
# Test

[//]: # (This is a comment)
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_custom_ignored_definitions(self, rule: MD053) -> None:
        """Custom ignored definitions are not flagged."""
        content = """\
# Test

[ignored1]: https://example.com
[ignored2]: https://example.com
[not-ignored]: https://example.com
"""
        doc = Document(Path("test.md"), content)
        config = MD053Config(ignored_definitions=["ignored1", "ignored2"])

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "not-ignored" in violations[0].message

    def test_case_insensitive_label_matching(self, rule: MD053, config: MD053Config) -> None:
        """Reference labels are matched case-insensitively."""
        content = """\
A [EXAMPLE] link.

[example]: https://example.com
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_case_insensitive_duplicate_detection(self, rule: MD053, config: MD053Config) -> None:
        """Duplicate definitions are detected case-insensitively."""
        content = """\
A [example].

[example]: https://example.com
[EXAMPLE]: https://example.com
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 4
        assert "Duplicate" in violations[0].message

    def test_reference_in_code_block_not_counted(self, rule: MD053, config: MD053Config) -> None:
        """References inside code blocks do not count as uses."""
        content = """\
```
[example]
```

[example]: https://example.com
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "Unused" in violations[0].message

    def test_definition_in_code_block_not_counted(self, rule: MD053, config: MD053Config) -> None:
        """Definitions inside code blocks are not counted as definitions."""
        content = """\
```
[example]: https://example.com
```
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_uses_of_same_definition(self, rule: MD053, config: MD053Config) -> None:
        """A definition used multiple times is valid."""
        content = """\
A [example] link and another [example] link.

[example]: https://example.com
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_violation_context(self, rule: MD053, config: MD053Config) -> None:
        """Violations include the line content as context."""
        content = """\
# Test

[unused]: https://example.com
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) > 0
        assert violations[0].context == "[unused]: https://example.com"

    def test_reference_in_inline_code_not_counted(self, rule: MD053, config: MD053Config) -> None:
        """References inside inline code spans do not count as uses."""
        content = load_fixture("md053", "inline_code_shortcut.md")
        doc = Document(Path("inline_code_shortcut.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "Unused" in violations[0].message
        assert "example" in violations[0].message

    def test_full_reference_in_inline_code_not_counted(
        self, rule: MD053, config: MD053Config
    ) -> None:
        """Full reference links inside inline code spans do not count as uses."""
        content = load_fixture("md053", "inline_code_full.md")
        doc = Document(Path("inline_code_full.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "Unused" in violations[0].message

    def test_reference_in_html_comment_not_counted(self, rule: MD053, config: MD053Config) -> None:
        """References inside HTML comments do not count as uses."""
        content = load_fixture("md053", "html_comment.md")
        doc = Document(Path("html_comment.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "Unused" in violations[0].message

    def test_collapsed_image_reference_used(self, rule: MD053, config: MD053Config) -> None:
        """Collapsed image reference ![alt][] marks definition as used."""
        content = load_fixture("md053", "collapsed_image.md")
        doc = Document(Path("collapsed_image.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_shortcut_image_reference_used(self, rule: MD053, config: MD053Config) -> None:
        """Shortcut image reference ![alt] marks definition as used."""
        content = load_fixture("md053", "shortcut_image.md")
        doc = Document(Path("shortcut_image.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_empty_document(self, rule: MD053, config: MD053Config) -> None:
        """Empty document produces no violations."""
        doc = Document(Path("test.md"), "")

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_only_definitions(self, rule: MD053, config: MD053Config) -> None:
        """Document with only definitions flags all as unused."""
        content = load_fixture("md053", "only_definitions.md")
        doc = Document(Path("only_definitions.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert all("Unused" in v.message for v in violations)

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = MD053Config()

        assert config.ignored_definitions == ["//"]

    def test_fix_removes_unused_and_duplicate(self, rule: MD053, config: MD053Config) -> None:
        """Fix removes unused and duplicate reference definitions."""
        content = load_fixture("md053", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []
        # The used definition should remain
        assert "[example]: https://example.com" in result
        # Unused and duplicate definitions should be gone
        assert "[unused]:" not in result
        assert "duplicate.example.com" not in result

    def test_fix_returns_none_for_valid(self, rule: MD053, config: MD053Config) -> None:
        """Fix returns None when document is already valid."""
        content = load_fixture("md053", "valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_removes_all_unused_definitions(self, rule: MD053, config: MD053Config) -> None:
        """Fix removes all unused definitions from document with only definitions."""
        content = load_fixture("md053", "only_definitions.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_collapses_extra_blank_lines(self, rule: MD053, config: MD053Config) -> None:
        """Fix collapses extra blank lines left by removed definitions."""
        content = """\
# Test

Some text.

[unused]: https://example.com

More text.
"""
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        # Should not have double blank lines
        assert "\n\n\n" not in result
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_preserves_ignored_definitions(self, rule: MD053, config: MD053Config) -> None:
        """Fix preserves ignored (comment-style) definitions."""
        content = """\
# Test

[//]: # (This is a comment)

[unused]: https://example.com
"""
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert "[//]: # (This is a comment)" in result
        assert "[unused]:" not in result

    def test_fix_keeps_first_duplicate(self, rule: MD053, config: MD053Config) -> None:
        """Fix removes duplicate definitions but keeps the first one."""
        content = """\
A [example].

[example]: https://first.example.com
[example]: https://second.example.com
"""
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        assert "https://first.example.com" in result
        assert "https://second.example.com" not in result

    def test_fix_does_not_touch_code_blocks(self, rule: MD053, config: MD053Config) -> None:
        """Fix does not remove definitions inside code blocks."""
        content = """\
```
[example]: https://example.com
```
"""
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_preserves_preexisting_blank_lines(self, rule: MD053, config: MD053Config) -> None:
        """Fix does not collapse pre-existing consecutive blank lines."""
        content = """\
# Test


Two blank lines above are pre-existing.

[unused]: https://example.com

More text.
"""
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        # Pre-existing double blank line should be preserved
        assert "\n\n\n" in result
        assert "[unused]:" not in result
