import json
from pathlib import Path

from rich.console import Console

from mdlint.linter import FileResult, LintResult
from mdlint.output.json import format_json
from mdlint.output.terminal import print_results
from mdlint.violation import Violation


class TestJSONFormatter:
    """Tests for JSON output formatter."""

    def test_format_empty_result(self) -> None:
        """Format empty result."""
        result = LintResult()

        output = format_json(result)
        parsed = json.loads(output)

        assert parsed["files"] == []
        assert parsed["summary"]["files_checked"] == 0
        assert parsed["summary"]["total_violations"] == 0
        assert parsed["summary"]["exit_code"] == 0

    def test_format_with_violations(self) -> None:
        """Format result with violations."""
        violation = Violation(
            line=10,
            column=1,
            rule_id="MD001",
            rule_name="heading-increment",
            message="Test message",
            context="### Heading",
        )
        file_result = FileResult(path=Path("test.md"), violations=[violation])
        result = LintResult(files=[file_result])

        output = format_json(result)
        parsed = json.loads(output)

        assert len(parsed["files"]) == 1
        assert len(parsed["files"][0]["violations"]) == 1
        assert parsed["files"][0]["violations"][0]["rule_id"] == "MD001"
        assert parsed["summary"]["total_violations"] == 1
        assert parsed["summary"]["exit_code"] == 1

    def test_format_with_error(self) -> None:
        """Format result with file error."""
        file_result = FileResult(path=Path("missing.md"), error="File not found")
        result = LintResult(files=[file_result])

        output = format_json(result)
        parsed = json.loads(output)

        assert parsed["files"][0]["error"] == "File not found"
        assert parsed["summary"]["files_with_errors"] == 1


def _capture_terminal_output(result: LintResult, show_context: bool = False) -> str:
    """Helper to capture terminal output as plain text (no ANSI codes)."""
    console = Console(no_color=True, highlight=False, width=120)
    with console.capture() as capture:
        print_results(result, console=console, show_context=show_context)
    return capture.get()


class TestTerminalContext:
    """Tests for terminal output with --show-context."""

    SAMPLE_CONTENT = "# Heading\n\nSome text here.\n\nAnother paragraph.\n\nFinal line.\n"

    def test_context_shows_surrounding_lines(self) -> None:
        """Context shows ±2 surrounding lines with line numbers."""
        violation = Violation(line=4, column=1, rule_id="MD001", rule_name="test", message="Test")
        file_result = FileResult(
            path=Path("test.md"),
            violations=[violation],
            content=self.SAMPLE_CONTENT,
        )
        result = LintResult(files=[file_result])

        output = _capture_terminal_output(result, show_context=True)

        assert "2: " in output
        assert "3: Some text here." in output
        assert "4: " in output  # violation line (blank in content)
        assert "5: Another paragraph." in output
        assert "6: " in output
        assert "^" in output

    def test_context_at_first_line(self) -> None:
        """Context at line 1 doesn't go negative."""
        violation = Violation(line=1, column=1, rule_id="MD001", rule_name="test", message="Test")
        file_result = FileResult(
            path=Path("test.md"),
            violations=[violation],
            content=self.SAMPLE_CONTENT,
        )
        result = LintResult(files=[file_result])

        output = _capture_terminal_output(result, show_context=True)

        assert "1: # Heading" in output
        assert "2: " in output
        assert "3: Some text here." in output
        assert "^" in output

    def test_context_at_last_line(self) -> None:
        """Context at last line doesn't exceed total lines."""
        content = "Line 1\nLine 2\nLine 3\n"
        violation = Violation(line=3, column=1, rule_id="MD001", rule_name="test", message="Test")
        file_result = FileResult(
            path=Path("test.md"),
            violations=[violation],
            content=content,
        )
        result = LintResult(files=[file_result])

        output = _capture_terminal_output(result, show_context=True)

        assert "1: Line 1" in output
        assert "2: Line 2" in output
        assert "3: Line 3" in output
        assert "^" in output

    def test_context_caret_at_column(self) -> None:
        """Caret appears at the correct column."""
        content = "Some text here\n"
        violation = Violation(line=1, column=6, rule_id="MD001", rule_name="test", message="Test")
        file_result = FileResult(
            path=Path("test.md"),
            violations=[violation],
            content=content,
        )
        result = LintResult(files=[file_result])

        output = _capture_terminal_output(result, show_context=True)

        lines = output.split("\n")
        caret_lines = [line for line in lines if line.strip() == "^"]
        assert len(caret_lines) == 1
        # Caret position: indent(4) + line_num_width(1) + ": "(2) + column-1(5) = 12
        assert caret_lines[0].index("^") == 12

    def test_no_context_without_flag(self) -> None:
        """Context is not shown when show_context is False."""
        violation = Violation(line=1, column=1, rule_id="MD001", rule_name="test", message="Test")
        file_result = FileResult(
            path=Path("test.md"),
            violations=[violation],
            content="# Heading\n",
        )
        result = LintResult(files=[file_result])

        output = _capture_terminal_output(result, show_context=False)

        assert "# Heading" not in output
        assert "^" not in output

    def test_no_context_without_content(self) -> None:
        """Context is not shown when content is None."""
        violation = Violation(line=1, column=1, rule_id="MD001", rule_name="test", message="Test")
        file_result = FileResult(
            path=Path("test.md"),
            violations=[violation],
        )
        result = LintResult(files=[file_result])

        output = _capture_terminal_output(result, show_context=True)

        assert "^" not in output

    def test_context_with_stdin(self) -> None:
        """Context works with stdin path."""
        content = "# Heading\nBad line\n"
        violation = Violation(line=2, column=1, rule_id="MD001", rule_name="test", message="Test")
        file_result = FileResult(
            path=Path("<stdin>"),
            violations=[violation],
            content=content,
        )
        result = LintResult(files=[file_result])

        output = _capture_terminal_output(result, show_context=True)

        assert "stdin" in output
        assert "1: # Heading" in output
        assert "2: Bad line" in output
        assert "^" in output
