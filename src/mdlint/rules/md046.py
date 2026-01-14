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

    def check(self, document: Document, config: MD046Config) -> list[Violation]:
        """Check for code block style consistency."""
        violations: list[Violation] = []

        expected_style: str | None = None
        if config.style in ("fenced", "indented"):
            expected_style = config.style

        for token in document.tokens:
            # fence = fenced code block (```)
            # code_block = indented code block (4 spaces)
            if token.type not in ("fence", "code_block"):
                continue

            if not token.map:
                continue

            line = token.map[0] + 1
            current_style = "fenced" if token.type == "fence" else "indented"

            if expected_style is None:
                expected_style = current_style
                continue

            if current_style != expected_style:
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
