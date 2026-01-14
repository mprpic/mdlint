from dataclasses import dataclass, field
from typing import Literal

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD048Config(RuleConfig):
    """Configuration for MD048 rule."""

    FenceStyle = Literal["consistent", "backtick", "tilde"]

    style: FenceStyle = field(
        default="consistent",
        metadata={
            "description": "Code fence style to enforce.",
            "option_descriptions": {
                "consistent": "All fences must match the first one used",
                "backtick": "All fences must use backticks (```)",
                "tilde": "All fences must use tildes (~~~)",
            },
        },
    )


class MD048(Rule[MD048Config]):
    """Code fence style should be consistent."""

    id = "MD048"
    name = "code-fence-style"
    summary = "Code fence style should be consistent"
    config_class = MD048Config

    description = (
        "This rule enforces that fenced code blocks use a consistent style "
        "throughout the document. Code fences can use either backticks (```) "
        "or tildes (~~~), but mixing styles within a document is discouraged."
    )

    rationale = (
        "Consistent formatting makes it easier to understand a document. "
        "Using the same fence style throughout promotes readability and "
        "maintains a uniform appearance in the source Markdown."
    )

    example_valid = """\
# Consistent Code Fences

All code blocks use backticks:

```python
def hello():
    print("Hello")
```

```bash
echo "Hello"
```

```json
{"key": "value"}
```
"""

    example_invalid = """\
# Inconsistent Code Fences

First code block uses backticks:

```python
def hello():
    print("Hello")
```

Second code block uses tildes:

~~~bash
echo "Hello"
~~~
"""

    MARKUP_TO_STYLE = {
        "`": "backtick",
        "~": "tilde",
    }

    def check(self, document: Document, config: MD048Config) -> list[Violation]:
        """Check for code fence style consistency."""
        violations: list[Violation] = []

        style = config.style
        expected_style: str | None = None

        if style in ("backtick", "tilde"):
            expected_style = style

        for token in document.tokens:
            if token.type != "fence":
                continue

            if not token.map or not token.markup:
                continue

            line = token.map[0] + 1  # 1-indexed line number
            fence_char = token.markup[0]  # First character of markup (` or ~)
            current_style = self.MARKUP_TO_STYLE.get(fence_char, "backtick")

            if expected_style is None:
                # Consistent mode: use first fence's style
                expected_style = current_style
            elif current_style != expected_style:
                violations.append(
                    Violation(
                        line=line,
                        column=1,
                        rule_id=self.id,
                        rule_name=self.name,
                        message=(
                            f"Code fence style: expected {expected_style}, found {current_style}"
                        ),
                        context=document.get_line(line),
                    )
                )

        return violations
