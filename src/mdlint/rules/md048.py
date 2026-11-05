import re
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

    CHAR_TO_STYLE = {
        "`": "backtick",
        "~": "tilde",
    }

    STYLE_TO_CHAR = {
        "backtick": "`",
        "tilde": "~",
    }

    def _get_expected_char(self, document: Document, config: MD048Config) -> str | None:
        """Determine the expected fence character from config or the first fence."""
        if config.style in self.STYLE_TO_CHAR:
            return self.STYLE_TO_CHAR[config.style]
        # Consistent mode: use the first fence's character
        for token in document.tokens:
            if token.type == "fence" and token.markup:
                return token.markup[0]
        return None

    def check(self, document: Document, config: MD048Config) -> list[Violation]:
        """Check for code fence style consistency."""
        violations: list[Violation] = []

        expected_char = self._get_expected_char(document, config)
        if expected_char is None:
            return violations

        expected_style = self.CHAR_TO_STYLE[expected_char]

        for token in document.tokens:
            if token.type != "fence":
                continue

            if not token.map or not token.markup:
                continue

            fence_char = token.markup[0]
            if fence_char != expected_char:
                line = token.map[0] + 1
                current_style = self.CHAR_TO_STYLE.get(fence_char, "backtick")
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

    def fix(self, document: Document, config: MD048Config) -> str | None:
        """Fix code fence style by converting all fences to the expected style.

        A fence is left as it is when a backtick fence cannot carry its info string.
        """
        violations = self.check(document, config)
        if not violations:
            return None

        expected_char = self._get_expected_char(document, config)
        assert expected_char is not None

        violation_lines = {v.line for v in violations}
        closing_line = re.compile(rf"[ \t]*({re.escape(expected_char)}+)[ \t]*")

        lines = document.content.split("\n")
        for token in document.tokens:
            if token.type != "fence" or not token.map or not token.markup:
                continue

            start, end = token.map
            if start + 1 not in violation_lines:
                continue
            if expected_char == "`" and "`" in token.info:
                continue  # a backtick fence's info string cannot contain backticks

            code_lines = token.content.removesuffix("\n").split("\n") if token.content else []
            # A code line made of the new fence character would close a fence no longer than it.
            runs = [len(m.group(1)) for line in code_lines if (m := closing_line.fullmatch(line))]
            length = max([len(token.markup)] + [run + 1 for run in runs])

            fence_lines = [start]
            if end - start - 1 > len(code_lines):
                fence_lines.append(end - 1)  # the fence is closed

            # Both fence lines change together, or the block would lose its closing fence.
            new_lines = []
            for index in fence_lines:
                prefix_length = len(document.container_prefix(index + 1))
                new_line = self._replace_fence(
                    lines[index], prefix_length, token.markup, expected_char * length
                )
                if new_line is None:
                    break
                new_lines.append(new_line)
            else:
                for index, new_line in zip(fence_lines, new_lines, strict=True):
                    lines[index] = new_line

        result = "\n".join(lines)
        if result == document.content:
            return None
        return result

    @staticmethod
    def _replace_fence(line: str, prefix_length: int, markup: str, new_fence: str) -> str | None:
        """Swap the fence run on a line for `new_fence`, or return None if it is not found.

        A closing run longer than `new_fence` keeps its length so it still closes the block.
        """
        start = prefix_length
        while start < len(line) and line[start] in " \t":
            start += 1
        end = start
        while end < len(line) and line[end] == markup[0]:
            end += 1
        if end - start < len(markup):
            return None
        return line[:start] + new_fence[0] * max(len(new_fence), end - start) + line[end:]
