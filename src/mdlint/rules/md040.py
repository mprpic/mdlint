from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD040Config(RuleConfig):
    """Configuration for MD040 rule."""

    allowed_languages: list[str] = field(
        default_factory=list,
        metadata={
            "description": "List of allowed language identifiers. Empty list allows any.",
        },
    )
    language_only: bool = field(
        default=False,
        metadata={
            "description": "When True, only the language identifier is allowed (no metadata "
            'such as `python hl_lines="3-5"`).',
        },
    )


class MD040(Rule[MD040Config]):
    """Fenced code blocks should have a language identifier specified."""

    id = "MD040"
    name = "fenced-code-language"
    summary = "Fenced code blocks should have a language identifier specified"
    config_class = MD040Config

    description = (
        "This rule enforces that fenced code blocks include a language identifier "
        "after the opening fence. The language identifier enables proper syntax "
        "highlighting in documentation viewers and code editors."
    )

    rationale = (
        "Specifying a language identifier improves content rendering by using the correct "
        "syntax highlighting for code. This helps readers quickly identify the "
        "code type and allows tools to apply appropriate formatting. For plain "
        "text blocks, use `text` as the language identifier."
    )

    example_valid = """\
# Valid Code Blocks

Code blocks with language specified:

```python
def hello():
    print("Hello, World!")
```

```bash
echo "Hello"
```

```json
{"key": "value"}
```
"""

    example_invalid = """\
# Invalid Code Blocks

Code block without language:

```
def hello():
    print("Hello, World!")
```
"""

    def check(self, document: Document, config: MD040Config) -> list[Violation]:
        """Check for fenced code blocks without language identifiers."""
        violations: list[Violation] = []

        for token in document.tokens:
            # Only check fenced code blocks, not indented code blocks
            if token.type != "fence":
                continue

            if not token.map:
                continue

            line = token.map[0] + 1  # 1-indexed line number
            info = token.info.strip() if token.info else ""

            # Check if language is missing
            if not info:
                violations.append(
                    Violation(
                        line=line,
                        column=1,
                        rule_id=self.id,
                        rule_name=self.name,
                        message="Fenced code block without language specified",
                        context=document.get_line(line),
                    )
                )
                continue

            # Extract just the language (first word in info string)
            language = info.split()[0]

            # Check allowed_languages if configured
            if config.allowed_languages and language not in config.allowed_languages:
                allowed = ", ".join(config.allowed_languages)
                violations.append(
                    Violation(
                        line=line,
                        column=1,
                        rule_id=self.id,
                        rule_name=self.name,
                        message=f"Language '{language}' not in allowed list: {allowed}",
                        context=document.get_line(line),
                    )
                )
                continue

            # Check language_only if configured
            if config.language_only and info != language:
                violations.append(
                    Violation(
                        line=line,
                        column=1,
                        rule_id=self.id,
                        rule_name=self.name,
                        message=(
                            f"Fenced code block info string contains extra metadata: "
                            f"'{info}' (expected only '{language}')"
                        ),
                        context=document.get_line(line),
                    )
                )

        return violations
