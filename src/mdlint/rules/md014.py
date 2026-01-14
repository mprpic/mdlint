import re
from dataclasses import dataclass

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD014Config(RuleConfig):
    """Configuration for MD014 rule."""


class MD014(Rule[MD014Config]):
    """Dollar signs used before commands without showing output."""

    id = "MD014"
    name = "commands-show-output"
    summary = "Dollar signs used before commands without showing output"
    config_class = MD014Config

    description = (
        "This rule triggers when code blocks show shell commands preceded by "
        "dollar signs (`$`), but none of the commands show any output. The dollar "
        "signs are unnecessary in this case and make the code harder to copy/paste."
    )

    rationale = (
        "It is easier to copy/paste shell commands and less noisy if the dollar "
        "signs are omitted when they are not needed. Dollar signs are only useful "
        "when distinguishing between typed commands and their output."
    )

    example_valid = """\
# Valid Document

Commands without dollar signs:

```bash
ls
cat foo
less bar
```

Commands with output showing:

```bash
$ ls
foo bar
$ cat foo
Hello world
```
"""

    example_invalid = """\
# Invalid Document

All commands have dollar signs but no output:

```bash
$ ls
$ cat foo
$ less bar
```
"""

    DOLLAR_COMMAND_RE = re.compile(r"^(\s*)(\$\s+)")

    def check(self, document: Document, config: MD014Config) -> list[Violation]:
        """Check for unnecessary dollar signs in code blocks."""
        violations: list[Violation] = []

        for token in document.tokens:
            # Check both fenced and indented code blocks
            if token.type not in ("fence", "code_block"):
                continue

            if not token.content or not token.map:
                continue

            lines = token.content.split("\n")
            # Filter out empty lines for analysis
            non_empty_lines = [line for line in lines if line.strip()]

            if not non_empty_lines:
                continue

            # Check if all non-empty lines match the dollar sign pattern
            dollar_matches = []
            for line in non_empty_lines:
                match = self.DOLLAR_COMMAND_RE.match(line)
                dollar_matches.append(match)

            # Only report violations if ALL non-empty lines start with $ prompt
            if all(match is not None for match in dollar_matches):
                # Calculate the starting line number for content
                # For fenced blocks, content starts after the opening fence
                # For indented code blocks, content starts at map[0]
                if token.type == "fence":
                    content_start_line = token.map[0] + 2  # +1 for 0-index, +1 for fence line
                else:
                    content_start_line = token.map[0] + 1

                # Report a violation for each line with a dollar sign
                current_line = content_start_line
                for line in lines:
                    if line.strip():  # Only check non-empty lines
                        match = self.DOLLAR_COMMAND_RE.match(line)
                        if match:
                            # Column is after the leading whitespace
                            column = len(match.group(1)) + 1
                            msg = "Dollar sign before command without output"
                            violations.append(
                                Violation(
                                    line=current_line,
                                    column=column,
                                    rule_id=self.id,
                                    rule_name=self.name,
                                    message=msg,
                                    context=document.get_line(current_line),
                                )
                            )
                    current_line += 1

        return violations
