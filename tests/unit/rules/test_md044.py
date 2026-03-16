from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md044 import MD044, MD044Config
from tests.conftest import load_fixture


class TestMD044:
    @pytest.fixture
    def rule(self) -> MD044:
        return MD044()

    @pytest.fixture
    def config(self) -> MD044Config:
        return MD044Config(names=["JavaScript", "GitHub", "Python"])

    def test_valid_document(self, rule: MD044, config: MD044Config) -> None:
        """Valid document passes the rule."""
        content = load_fixture("md044", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD044, config: MD044Config) -> None:
        """Invalid document triggers violations."""
        content = load_fixture("md044", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 6
        assert violations[0].rule_id == "MD044"
        assert "javascript" in violations[0].message
        assert "JavaScript" in violations[0].message

    def test_no_names_configured(self, rule: MD044) -> None:
        """No violations when no names are configured."""
        content = "This has javascript and github mentions."
        doc = Document(Path("test.md"), content)
        config = MD044Config()

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_single_name(self, rule: MD044) -> None:
        """Single name configuration works."""
        content = "I love javascript!"
        doc = Document(Path("test.md"), content)
        config = MD044Config(names=["JavaScript"])

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "javascript" in violations[0].message
        assert "JavaScript" in violations[0].message

    def test_case_insensitive_matching(self, rule: MD044) -> None:
        """Names are matched case-insensitively."""
        content = "JAVASCRIPT and Javascript and javascript"
        doc = Document(Path("test.md"), content)
        config = MD044Config(names=["JavaScript"])

        violations = rule.check(doc, config)

        assert len(violations) == 3

    def test_code_blocks_excluded_by_default(self, rule: MD044) -> None:
        """Code blocks are excluded by default when code_blocks=False."""
        content = load_fixture("md044", "code_blocks.md")
        doc = Document(Path("code_blocks.md"), content)
        config = MD044Config(names=["JavaScript"], code_blocks=False)

        violations = rule.check(doc, config)

        # Should not flag javascript in fenced code block or inline code
        assert len(violations) == 0

    def test_code_blocks_included(self, rule: MD044) -> None:
        """Code blocks are checked when code_blocks=True."""
        content = load_fixture("md044", "code_blocks.md")
        doc = Document(Path("code_blocks.md"), content)
        config = MD044Config(names=["JavaScript"], code_blocks=True)

        violations = rule.check(doc, config)

        # Should flag javascript in code content and inline code, but not the fence info string
        assert len(violations) == 2

    def test_link_urls_excluded(self, rule: MD044) -> None:
        """URLs in links are not checked."""
        content = "[Click here](https://javascript.info)"
        doc = Document(Path("test.md"), content)
        config = MD044Config(names=["JavaScript"])

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_link_text_checked(self, rule: MD044) -> None:
        """Link text is checked."""
        content = "[javascript guide](https://example.com)"
        doc = Document(Path("test.md"), content)
        config = MD044Config(names=["JavaScript"])

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_word_boundary_matching(self, rule: MD044) -> None:
        """Names are matched as whole words."""
        content = "JavaScripting and preJavaScript"
        doc = Document(Path("test.md"), content)
        config = MD044Config(names=["JavaScript"])

        violations = rule.check(doc, config)

        # Should not match "JavaScripting" or "preJavaScript"
        assert len(violations) == 0

    def test_multiple_violations_same_line(self, rule: MD044) -> None:
        """Multiple violations on the same line are detected."""
        content = "Use javascript and github together"
        doc = Document(Path("test.md"), content)
        config = MD044Config(names=["JavaScript", "GitHub"])

        violations = rule.check(doc, config)

        assert len(violations) == 2

    def test_correct_column_positions(self, rule: MD044) -> None:
        """Violation column positions are correct."""
        content = "Use javascript here"
        doc = Document(Path("test.md"), content)
        config = MD044Config(names=["JavaScript"])

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].column == 5  # "javascript" starts at column 5

    def test_html_elements_excluded(self, rule: MD044) -> None:
        """HTML elements are excluded when html_elements=False."""
        content = "<div>javascript</div>"
        doc = Document(Path("test.md"), content)
        config = MD044Config(names=["JavaScript"], html_elements=False)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_html_elements_included(self, rule: MD044) -> None:
        """HTML elements are checked when html_elements=True."""
        content = "<div>javascript</div>"
        doc = Document(Path("test.md"), content)
        config = MD044Config(names=["JavaScript"], html_elements=True)

        violations = rule.check(doc, config)

        assert len(violations) == 1

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = MD044Config()

        assert config.names == []
        assert config.code_blocks is True
        assert config.html_elements is True

    def test_violation_context(self, rule: MD044) -> None:
        """Violations include the line content as context."""
        content = "Learn javascript today"
        doc = Document(Path("test.md"), content)
        config = MD044Config(names=["JavaScript"])

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].context == content

    def test_multiple_correct_forms(self, rule: MD044) -> None:
        """Multiple correct forms of the same name are allowed."""
        content = "Visit github.com or GitHub for more info."
        doc = Document(Path("test.md"), content)
        config = MD044Config(names=["GitHub", "github.com"])

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_names_with_special_characters(self, rule: MD044) -> None:
        """Names with special characters are matched correctly."""
        content = "Visit Github.com for more info."
        doc = Document(Path("test.md"), content)
        config = MD044Config(names=["github.com"])

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert "Github.com" in violations[0].message

    def test_reference_links_excluded(self, rule: MD044) -> None:
        """Reference link definitions are excluded."""
        content = """\
Check out [javascript][1] for more.

[1]: https://javascript.info "javascript guide"
"""
        doc = Document(Path("test.md"), content)
        config = MD044Config(names=["JavaScript"])

        violations = rule.check(doc, config)

        # Should only flag the link text, not the URL or title
        assert len(violations) == 1
        assert violations[0].line == 1

    def test_fence_info_string_excluded(self, rule: MD044) -> None:
        """Fence info strings are not checked even with code_blocks=True."""
        content = "```javascript\nconsole.log(1);\n```\n"
        doc = Document(Path("test.md"), content)
        config = MD044Config(names=["JavaScript"], code_blocks=True)

        violations = rule.check(doc, config)

        # Should not flag the info string; no violations in this content
        assert len(violations) == 0

    def test_autolink_excluded(self, rule: MD044) -> None:
        """Autolinks are not checked."""
        content = "Visit <https://javascript.info> for more."
        doc = Document(Path("test.md"), content)
        config = MD044Config(names=["JavaScript"])

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_front_matter_excluded(self, rule: MD044) -> None:
        """Front matter content is not checked."""
        content = "---\ntitle: javascript guide\n---\n\n# Hello\n"
        doc = Document(Path("test.md"), content)
        config = MD044Config(names=["JavaScript"])

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_fix_corrects_invalid(self, rule: MD044, config: MD044Config) -> None:
        """Fixing invalid content produces valid output."""
        content = load_fixture("md044", "invalid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is not None
        # Verify the names are corrected
        assert "JavaScript" in result
        assert "GitHub" in result
        assert "Python" in result
        assert "javascript" not in result
        assert "github" not in result
        assert "python" not in result
        # Verify no violations remain
        fixed_doc = Document(Path("test.md"), result)
        assert rule.check(fixed_doc, config) == []

    def test_fix_returns_none_for_valid(self, rule: MD044, config: MD044Config) -> None:
        """Fixing already-valid content returns None."""
        content = load_fixture("md044", "valid.md")
        doc = Document(Path("test.md"), content)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_multiple_on_same_line(self, rule: MD044) -> None:
        """Fix handles multiple violations on the same line."""
        content = "Use javascript and github together"
        doc = Document(Path("test.md"), content)
        config = MD044Config(names=["JavaScript", "GitHub"])
        result = rule.fix(doc, config)
        assert result == "Use JavaScript and GitHub together"

    def test_fix_case_variants(self, rule: MD044) -> None:
        """Fix handles different case variants."""
        content = "JAVASCRIPT and Javascript and javascript"
        doc = Document(Path("test.md"), content)
        config = MD044Config(names=["JavaScript"])
        result = rule.fix(doc, config)
        assert result == "JavaScript and JavaScript and JavaScript"

    def test_fix_preserves_code_blocks_when_excluded(self, rule: MD044) -> None:
        """Fix does not modify code blocks when code_blocks=False."""
        content = load_fixture("md044", "code_blocks.md")
        doc = Document(Path("test.md"), content)
        config = MD044Config(names=["JavaScript"], code_blocks=False)
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_link_text_not_url(self, rule: MD044) -> None:
        """Fix corrects link text but not URL."""
        content = "[javascript guide](https://javascript.info)"
        doc = Document(Path("test.md"), content)
        config = MD044Config(names=["JavaScript"])
        result = rule.fix(doc, config)
        assert result == "[JavaScript guide](https://javascript.info)"

    def test_fix_no_names_configured(self, rule: MD044) -> None:
        """Fix returns None when no names are configured."""
        content = "This has javascript mentions."
        doc = Document(Path("test.md"), content)
        config = MD044Config()
        result = rule.fix(doc, config)
        assert result is None

    def test_fix_special_characters_in_name(self, rule: MD044) -> None:
        """Fix handles names with special characters."""
        content = "Visit Github.com for more info."
        doc = Document(Path("test.md"), content)
        config = MD044Config(names=["github.com"])
        result = rule.fix(doc, config)
        assert result == "Visit github.com for more info."
