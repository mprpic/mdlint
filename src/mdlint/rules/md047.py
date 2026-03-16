from dataclasses import dataclass

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD047Config(RuleConfig):
    """Configuration for MD047 rule."""


class MD047(Rule[MD047Config]):
    """Files should end with a single newline character."""

    id = "MD047"
    name = "single-trailing-newline"
    summary = "Files should end with a single newline character"
    config_class = MD047Config

    description = (
        "This rule is triggered when there is no newline character at the "
        "end of a file. The file should end with exactly one newline character."
    )

    rationale = (
        "Some programs have trouble with files that do not end with a newline. "
        "POSIX defines a line as a sequence of characters followed by a newline, "
        "so the final line without a newline is technically not a complete line. "
        "Additionally, when viewing files in a terminal or concatenating them, "
        "missing trailing newlines can cause unexpected formatting issues."
    )

    def check(self, document: Document, config: MD047Config) -> list[Violation]:
        """Check for missing trailing newline."""
        violations: list[Violation] = []

        content = document.content

        # Empty file is valid
        if not content:
            return violations

        # Check if file ends with newline
        if not content.endswith("\n"):
            # Get the last line number and content
            last_line_num = len(document.lines)
            last_line = document.lines[-1] if document.lines else ""

            # Column is at the end of the last line (where newline should be)
            column = len(last_line) + 1

            violations.append(
                Violation(
                    line=last_line_num,
                    column=column,
                    rule_id=self.id,
                    rule_name=self.name,
                    message="File should end with a single newline character",
                    context=document.get_line(last_line_num),
                )
            )

        return violations

    def fix(self, document: Document, config: MD047Config) -> str | None:
        """Fix missing trailing newline by appending one."""
        content = document.content

        if not content or content.endswith("\n"):
            return None

        return content + "\n"
