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

    def _find_dollar_blocks(self, document: Document) -> list[tuple[int, int, list[str]]]:
        """Find code blocks where all non-empty lines start with a dollar sign.

        Returns a list of (content_start, content_end, content_lines) tuples where
        content_start and content_end are 0-indexed line indices into the document.
        """
        results: list[tuple[int, int, list[str]]] = []

        for token in document.tokens:
            if token.type not in ("fence", "code_block"):
                continue

            if not token.content or not token.map:
                continue

            content_lines = token.content.split("\n")
            non_empty_lines = [line for line in content_lines if line.strip()]

            if not non_empty_lines:
                continue

            if not all(self.DOLLAR_COMMAND_RE.match(line) for line in non_empty_lines):
                continue

            if token.type == "fence":
                content_start = token.map[0] + 1  # line after opening fence
                content_end = token.map[1] - 1  # exclude closing fence
            else:
                content_start = token.map[0]
                content_end = token.map[1]

            results.append((content_start, content_end, content_lines))

        return results

    def check(self, document: Document, config: MD014Config) -> list[Violation]:
        """Check for unnecessary dollar signs in code blocks."""
        violations: list[Violation] = []

        for content_start, content_end, content_lines in self._find_dollar_blocks(document):
            # content_start is 0-indexed; violation lines are 1-indexed
            current_line = content_start + 1
            for line in content_lines:
                if line.strip():
                    match = self.DOLLAR_COMMAND_RE.match(line)
                    if match:
                        column = len(match.group(1)) + 1
                        violations.append(
                            Violation(
                                line=current_line,
                                column=column,
                                rule_id=self.id,
                                rule_name=self.name,
                                message="Dollar sign before command without output",
                                context=document.get_line(current_line),
                            )
                        )
                current_line += 1

        return violations

    def fix(self, document: Document, config: MD014Config) -> str | None:
        """Fix by removing unnecessary dollar sign prefixes from code blocks."""
        dollar_blocks = self._find_dollar_blocks(document)
        if not dollar_blocks:
            return None

        lines = document.content.split("\n")

        for content_start, content_end, _ in dollar_blocks:
            for i in range(content_start, content_end):
                match = self.DOLLAR_COMMAND_RE.match(lines[i])
                if match:
                    lines[i] = match.group(1) + lines[i][match.end() :]

        return "\n".join(lines)
