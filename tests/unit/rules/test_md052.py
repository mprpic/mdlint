from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md052 import MD052, MD052Config
from tests.conftest import load_fixture


class TestMD052:
    @pytest.fixture
    def rule(self) -> MD052:
        return MD052()

    @pytest.fixture
    def config(self) -> MD052Config:
        return MD052Config()

    def test_valid_document(self, rule: MD052, config: MD052Config) -> None:
        """Valid document passes the rule."""
        content = load_fixture("md052", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD052, config: MD052Config) -> None:
        """Invalid document triggers violations."""
        content = load_fixture("md052", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 3
        assert violations[0].rule_id == "MD052"
        assert violations[0].line == 3
        assert "undefined" in violations[0].message.lower()
        assert violations[1].line == 5
        assert "missing" in violations[1].message.lower()
        assert violations[2].line == 7
        assert "no-image" in violations[2].message.lower()

    def test_full_reference_link_undefined(self, rule: MD052, config: MD052Config) -> None:
        """Full reference links with undefined labels are flagged."""
        content = """\
# Test

See [this link][undefined-ref] for more.

[other-ref]: https://example.com
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3
        assert "undefined-ref" in violations[0].message

    def test_collapsed_reference_link_undefined(self, rule: MD052, config: MD052Config) -> None:
        """Collapsed reference links with undefined labels are flagged."""
        content = """\
# Test

See [undefined][] for more.
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3
        assert "undefined" in violations[0].message

    def test_shortcut_syntax_disabled_by_default(self, rule: MD052, config: MD052Config) -> None:
        """Shortcut syntax is not checked by default."""
        content = load_fixture("md052", "shortcut_syntax.md")
        doc = Document(Path("shortcut_syntax.md"), content)

        violations = rule.check(doc, config)

        # Shortcut syntax should not trigger violations by default
        assert len(violations) == 0

    def test_shortcut_syntax_enabled(self, rule: MD052) -> None:
        """Shortcut syntax triggers violations when enabled."""
        content = load_fixture("md052", "shortcut_syntax.md")
        doc = Document(Path("shortcut_syntax.md"), content)
        config = MD052Config(shortcut_syntax=True)

        violations = rule.check(doc, config)

        # Both shortcut references should be flagged
        assert len(violations) == 2
        assert violations[0].line == 3
        assert "shortcut" in violations[0].message.lower()
        assert violations[1].line == 5
        assert "another-shortcut" in violations[1].message.lower()

    def test_ignored_labels_default(self, rule: MD052, config: MD052Config) -> None:
        """Default ignored labels include 'x' for task lists."""
        content = load_fixture("md052", "ignored_labels.md")
        doc = Document(Path("ignored_labels.md"), content)

        violations = rule.check(doc, config)

        # Only 'undefined' should be flagged, not 'x'
        assert len(violations) == 1
        assert "undefined" in violations[0].message.lower()

    def test_custom_ignored_labels(self, rule: MD052) -> None:
        """Custom ignored labels are respected."""
        content = """\
# Test

See [custom-ignore][] link.

And [flagged][] reference.
"""
        doc = Document(Path("test.md"), content)
        config = MD052Config(ignored_labels=["custom-ignore"])

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "flagged" in violations[0].message

    def test_image_reference_undefined(self, rule: MD052, config: MD052Config) -> None:
        """Image references with undefined labels are flagged."""
        content = """\
# Test

![alt text][no-such-image]
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "no-such-image" in violations[0].message

    def test_image_reference_collapsed(self, rule: MD052, config: MD052Config) -> None:
        """Collapsed image references with undefined labels are flagged."""
        content = """\
# Test

![missing][]
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "missing" in violations[0].message

    def test_defined_references_pass(self, rule: MD052, config: MD052Config) -> None:
        """Defined references do not trigger violations."""
        content = """\
# Test

[link][defined]

[defined]: https://example.com
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_case_insensitive_label_matching(self, rule: MD052, config: MD052Config) -> None:
        """Label matching is case-insensitive."""
        content = """\
# Test

[link][MyLabel]

[mylabel]: https://example.com
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_reference_in_code_block_ignored(self, rule: MD052, config: MD052Config) -> None:
        """References inside code blocks are not checked."""
        content = """\
# Test

```markdown
[undefined][ref]
```
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_reference_in_inline_code_ignored(self, rule: MD052, config: MD052Config) -> None:
        """References inside inline code are not checked."""
        content = """\
# Test

Use `[undefined][ref]` syntax for links.
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_references_same_label(self, rule: MD052, config: MD052Config) -> None:
        """Multiple uses of same undefined label are all flagged."""
        content = """\
# Test

[text1][undefined]

[text2][undefined]
"""
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 3
        assert violations[1].line == 5

    def test_violation_context(self, rule: MD052, config: MD052Config) -> None:
        """Violations include line content as context."""
        content = "[link][undefined]"
        doc = Document(Path("test.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].context == content

    def test_reference_in_html_comment_ignored(self, rule: MD052, config: MD052Config) -> None:
        """References inside HTML comments are not checked."""
        content = load_fixture("md052", "html_comment.md")
        doc = Document(Path("html_comment.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = MD052Config()

        assert config.shortcut_syntax is False
        assert config.ignored_labels == ["x"]
