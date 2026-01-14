from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md013 import MD013, MD013Config
from tests.conftest import load_fixture


class TestMD013:
    @pytest.fixture
    def rule(self) -> MD013:
        return MD013()

    @pytest.fixture
    def config(self) -> MD013Config:
        return MD013Config()

    def test_valid_document(self, rule: MD013, config: MD013Config) -> None:
        """Valid document with lines under the limit."""
        content = load_fixture("md013", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD013, config: MD013Config) -> None:
        """Invalid document with lines exceeding the limit."""
        content = load_fixture("md013", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].rule_id == "MD013"
        assert violations[0].line == 3
        assert "80" in violations[0].message
        assert violations[1].line == 5

    def test_long_url_exception(self, rule: MD013, config: MD013Config) -> None:
        """Lines with no whitespace beyond the limit are allowed."""
        content = load_fixture("md013", "long_url.md")
        doc = Document(Path("long_url.md"), content)

        violations = rule.check(doc, config)

        # Only the line with spaces beyond the limit should be flagged
        assert len(violations) == 1
        assert violations[0].line == 7

    def test_ignore_code_blocks(self, rule: MD013) -> None:
        """Test excluding code blocks from line length check."""
        content = load_fixture("md013", "code_block.md")
        doc = Document(Path("code_block.md"), content)
        config = MD013Config(code_blocks=False)

        violations = rule.check(doc, config)

        # Only the normal text line should be flagged
        assert len(violations) == 1
        assert violations[0].line == 9

    def test_include_code_blocks(self, rule: MD013, config: MD013Config) -> None:
        """Test including code blocks in line length check (default)."""
        content = load_fixture("md013", "code_block.md")
        doc = Document(Path("code_block.md"), content)

        violations = rule.check(doc, config)

        # Fenced code line has no spaces so is allowed, indented code and normal text flagged
        assert len(violations) == 2

    def test_ignore_headings(self, rule: MD013) -> None:
        """Test excluding headings from line length check."""
        content = load_fixture("md013", "headings.md")
        doc = Document(Path("headings.md"), content)
        config = MD013Config(headings=False)

        violations = rule.check(doc, config)

        # No violations when headings are excluded
        assert len(violations) == 0

    def test_include_headings(self, rule: MD013, config: MD013Config) -> None:
        """Test including headings in line length check (default)."""
        content = load_fixture("md013", "headings.md")
        doc = Document(Path("headings.md"), content)

        violations = rule.check(doc, config)

        # Both long headings should be flagged
        assert len(violations) == 2
        assert violations[0].line == 1
        assert violations[1].line == 5

    def test_ignore_tables(self, rule: MD013) -> None:
        """Test excluding tables from line length check."""
        content = load_fixture("md013", "tables.md")
        doc = Document(Path("tables.md"), content)
        config = MD013Config(tables=False)

        violations = rule.check(doc, config)

        # No violations when tables are excluded
        assert len(violations) == 0

    def test_include_tables(self, rule: MD013, config: MD013Config) -> None:
        """Test including tables in line length check (default)."""
        content = load_fixture("md013", "tables.md")
        doc = Document(Path("tables.md"), content)

        violations = rule.check(doc, config)

        # Header (line 3) and data (line 5) rows have spaces and are flagged;
        # separator row (line 4) has no whitespace so passes wrapping check
        assert len(violations) == 2
        assert violations[0].line == 3
        assert violations[1].line == 5

    def test_custom_line_length(self, rule: MD013) -> None:
        """Test with custom line length."""
        content = load_fixture("md013", "custom_length.md")
        doc = Document(Path("custom_length.md"), content)
        config = MD013Config(line_length=40)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 4
        assert violations[0].message == "Expected max 40 characters, found 54"

    def test_strict_mode(self, rule: MD013) -> None:
        """Test strict mode that flags all long lines."""
        content = load_fixture("md013", "strict_mode.md")
        doc = Document(Path("strict_mode.md"), content)
        config = MD013Config(strict=True)

        violations = rule.check(doc, config)

        # Both long lines should be flagged in strict mode
        assert len(violations) == 2
        assert violations[0].line == 3
        assert violations[1].line == 5

    def test_default_mode_allows_no_space_lines(self, rule: MD013, config: MD013Config) -> None:
        """Test that default mode allows lines with no spaces beyond limit."""
        content = load_fixture("md013", "strict_mode.md")
        doc = Document(Path("strict_mode.md"), content)

        violations = rule.check(doc, config)

        # Only the line with spaces beyond the limit
        assert len(violations) == 1
        assert violations[0].line == 5

    def test_heading_line_length(self, rule: MD013) -> None:
        """Test separate line length for headings."""
        content = load_fixture("md013", "headings.md")
        doc = Document(Path("headings.md"), content)
        config = MD013Config(heading_line_length=100)

        violations = rule.check(doc, config)

        # Only the first heading (89 chars) should pass, second (94 chars) too
        assert len(violations) == 0

    def test_code_block_line_length(self, rule: MD013) -> None:
        """Test separate line length for code blocks."""
        content = load_fixture("md013", "code_block.md")
        doc = Document(Path("code_block.md"), content)
        config = MD013Config(code_block_line_length=120)

        violations = rule.check(doc, config)

        # Code blocks have higher limit, only normal text should be flagged
        assert len(violations) == 1
        assert violations[0].line == 9

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = MD013Config()

        assert config.line_length == 80
        assert config.heading_line_length == 80
        assert config.code_block_line_length == 80
        assert config.code_blocks is True
        assert config.tables is True
        assert config.headings is True
        assert config.strict is False

    def test_violation_message(self, rule: MD013, config: MD013Config) -> None:
        """Test violation message format."""
        content = load_fixture("md013", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].message == "Expected max 80 characters, found 87"
        assert violations[1].message == "Expected max 80 characters, found 92"

    def test_boundary_line_length(self, rule: MD013, config: MD013Config) -> None:
        """Test lines at exactly the limit and one character over."""
        content = load_fixture("md013", "boundary.md")
        doc = Document(Path("boundary.md"), content)

        violations = rule.check(doc, config)

        # Line 1 (80 chars) is exactly at limit - no violation
        # Line 3 (81 chars) exceeds limit - violation
        assert len(violations) == 1
        assert violations[0].line == 3
        assert violations[0].column == 81
        assert violations[0].message == "Expected max 80 characters, found 81"

    def test_setext_headings(self, rule: MD013, config: MD013Config) -> None:
        """Test that setext headings are detected and checked."""
        content = load_fixture("md013", "setext_heading.md")
        doc = Document(Path("setext_heading.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 1
        assert violations[1].line == 6

    def test_setext_headings_excluded(self, rule: MD013) -> None:
        """Test that setext headings are excluded when headings=False."""
        content = load_fixture("md013", "setext_heading.md")
        doc = Document(Path("setext_heading.md"), content)
        config = MD013Config(headings=False)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_reference_definitions_exempted(self, rule: MD013, config: MD013Config) -> None:
        """Test that reference definition lines are always exempt."""
        content = load_fixture("md013", "reference_def.md")
        doc = Document(Path("reference_def.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_reference_definitions_strict(self, rule: MD013) -> None:
        """Test that reference definitions are exempt even in strict mode."""
        content = load_fixture("md013", "reference_def.md")
        doc = Document(Path("reference_def.md"), content)
        config = MD013Config(strict=True)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_link_only_lines_exempted(self, rule: MD013, config: MD013Config) -> None:
        """Test that lines containing only links/images are exempt."""
        content = load_fixture("md013", "link_only.md")
        doc = Document(Path("link_only.md"), content)

        violations = rule.check(doc, config)

        # Line 1 (link only) and line 5 (image only) are exempt
        # Line 3 (text with link) is flagged
        assert len(violations) == 1
        assert violations[0].line == 3
