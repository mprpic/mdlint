from rich.console import Console
from rich.text import Text

from mdlint.linter import LintResult


def _pluralize(count: int, word: str) -> str:
    return f"{count} {word}{'s' if count != 1 else ''}"


def _print_context(
    console: Console,
    content: str,
    violation_line: int,
    violation_column: int,
) -> None:
    """Print surrounding context lines for a violation.

    Shows two lines around the violation with the violation line in bold
    and a red caret pointing to the violation column.
    """
    lines = content.split("\n")
    total_lines = len(lines)

    start = max(1, violation_line - 2)
    end = min(total_lines, violation_line + 2)

    line_num_width = len(str(end))
    indent = "    "

    for line_num in range(start, end + 1):
        line_content = lines[line_num - 1]
        prefix = f"{indent}{line_num:>{line_num_width}}: "
        text = Text()
        if line_num == violation_line:
            text.append(prefix)
            text.append(line_content, style="bold")
        else:
            text.append(prefix)
            text.append(line_content)
        console.print(text)

        if line_num == violation_line:
            caret_offset = len(indent) + line_num_width + 2 + violation_column - 1
            caret_text = Text(" " * caret_offset + "^", style="red")
            console.print(caret_text)


def print_results(
    result: LintResult,
    console: Console | None = None,
    show_context: bool = False,
) -> None:
    """Print linting results to terminal with Rich formatting.

    Args:
        result: The linting result to print.
        console: Optional Rich console to use. If None, creates a new Console.
        show_context: Whether to show surrounding lines for each violation.
    """
    if console is None:
        console = Console()

    max_lc_width = 0
    for f in result.files:
        for v in f.violations:
            max_lc_width = max(max_lc_width, len(f"{v.line}:{v.column}"))

    for file_result in result.files:
        if file_result.error:
            console.print(f"[red]{file_result.path}[/red]: Error: {file_result.error}")
            continue

        if not file_result.violations:
            continue

        # File header
        console.print(f"[bold]{file_result.path}[/bold] ({len(file_result.violations)})")

        # Violations
        for violation in file_result.violations:
            line_col = f"{violation.line}:{violation.column}"
            text = Text()
            text.append(f"{line_col:>{max_lc_width}}  ", style="dim")
            text.append(f"{violation.rule_id}  ", style="yellow")
            text.append(violation.message)
            console.print(text)

            if show_context and file_result.content is not None:
                console.print()
                _print_context(
                    console,
                    file_result.content,
                    violation.line,
                    violation.column,
                )
                console.print()

        console.print()  # Blank line between files

    # Summary line
    checked = _pluralize(result.files_checked, "file")
    if result.files_fixed > 0:
        fixed = _pluralize(result.files_fixed, "file")
        if result.total_violations > 0 or result.files_with_errors > 0:
            violations = _pluralize(result.total_violations, "violation")
            files = _pluralize(result.files_with_violations, "file")
            console.print(
                f"[green]✓[/green] Fixed {fixed}. "
                f"{violations} remaining in {files} ({checked} checked)"
            )
        else:
            console.print(f"[green]✓[/green] Fixed {fixed}. All files valid ({checked} checked)")
    elif result.total_violations > 0 or result.files_with_errors > 0:
        violations = _pluralize(result.total_violations, "violation")
        files = _pluralize(result.files_with_violations, "file")
        console.print(f"[red]✘[/red] Found {violations} in {files} ({checked} checked)")
    else:
        console.print(f"[green]✓[/green] All files valid ({checked} checked)")
