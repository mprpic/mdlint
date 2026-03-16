from dataclasses import dataclass, field
from typing import Literal

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD046Config(RuleConfig):
    """Configuration for MD046 rule."""

    CodeBlockStyle = Literal["consistent", "fenced", "indented"]

    style: CodeBlockStyle = field(
        default="fenced",
        metadata={
            "description": "Required code block style.",
            "option_descriptions": {
                "consistent": "All code blocks must match the first one used",
                "fenced": "All code blocks must use fenced style (triple backticks)",
                "indented": "All code blocks must use indented style (4 spaces)",
            },
        },
    )


class MD046(Rule[MD046Config]):
    """Code block style should be consistent."""

    id = "MD046"
    name = "code-block-style"
    summary = "Code block style should be consistent"
    config_class = MD046Config

    description = (
        "This rule ensures that code blocks throughout a document follow a "
        "consistent style. It validates that code blocks use either fenced "
        "style (triple backticks) or indented style (4 spaces) according to "
        "the configured preference."
    )

    rationale = (
        "Consistent formatting makes it easier to understand a document. "
        "Uniform code block styling improves the readability of code examples."
    )

    example_valid = """\
# Valid Code Blocks

All code blocks use fenced style:

```python
def hello():
    print("Hello, world!")
```

More text here.

```bash
echo "Fenced code block"
```
"""

    example_invalid = """\
# Mixed Code Block Styles

Fenced code block:

```python
def hello():
    print("Hello!")
```

Indented code block:

    echo "This is indented"
    ls -la
"""

    def _find_mismatched_blocks(self, document: Document, config: MD046Config) -> tuple[str, list]:
        """Return (expected_style, mismatched_tokens) for code blocks.

        Returns the resolved expected style and a list of tokens whose style
        does not match. Returns ("", []) if there are no code blocks.
        """
        expected_style: str | None = None
        if config.style in ("fenced", "indented"):
            expected_style = config.style

        mismatched = []
        for token in document.tokens:
            # fence = fenced code block (```)
            # code_block = indented code block (4 spaces)
            if token.type not in ("fence", "code_block"):
                continue
            if not token.map:
                continue

            current_style = "fenced" if token.type == "fence" else "indented"

            if expected_style is None:
                expected_style = current_style
                continue

            if current_style != expected_style:
                mismatched.append(token)

        return expected_style or "", mismatched

    def check(self, document: Document, config: MD046Config) -> list[Violation]:
        """Check for code block style consistency."""
        expected_style, mismatched = self._find_mismatched_blocks(document, config)
        violations: list[Violation] = []

        for token in mismatched:
            line = token.map[0] + 1
            current_style = "fenced" if token.type == "fence" else "indented"
            msg = f"Code block style: expected {expected_style}, found {current_style}"
            violations.append(
                Violation(
                    line=line,
                    column=1,
                    rule_id=self.id,
                    rule_name=self.name,
                    message=msg,
                    context=document.get_line(line),
                )
            )

        return violations

    def fix(self, document: Document, config: MD046Config) -> str | None:
        """Fix code block style by converting blocks to the configured style."""
        expected_style, tokens_to_fix = self._find_mismatched_blocks(document, config)

        if not tokens_to_fix:
            return None

        lines = document.content.split("\n")

        # Process in reverse order to maintain correct line numbers
        for token in reversed(tokens_to_fix):
            start, end = token.map

            if expected_style == "fenced":
                # Convert indented → fenced: remove 4-space indent, wrap in ```
                content_lines = []
                for i in range(start, end):
                    line = lines[i]
                    if line.startswith("    "):
                        content_lines.append(line[4:])
                    elif line.strip() == "":
                        content_lines.append("")
                    else:
                        content_lines.append(line)
                lines[start:end] = ["```"] + content_lines + ["```"]

            elif expected_style == "indented":
                # Convert fenced → indented: remove fence lines, add 4-space indent
                # Skip fenced blocks with indented fences (e.g. inside lists)
                if lines[start] != lines[start].lstrip():
                    continue

                content_lines = []
                for i in range(start + 1, end - 1):
                    line = lines[i]
                    if line.strip() == "":
                        content_lines.append("")
                    else:
                        content_lines.append("    " + line)
                lines[start:end] = content_lines

        result = "\n".join(lines)
        if result == document.content:
            return None
        return result
