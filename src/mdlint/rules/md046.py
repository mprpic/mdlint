import re
from dataclasses import dataclass, field
from typing import Literal

from markdown_it.token import Token

from mdlint.document import Document, is_blank_line
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation

_BACKTICK_RUN = re.compile(r"`+")

# Blocks after which indented code would be absorbed: a list item continues into it, and a
# code block separated from it only by blank lines merges with it.
_ABSORBING_PREVIOUS = ("bullet_list_open", "ordered_list_open", "code_block", "fence")


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
        """Fix code block style by converting blocks to the configured style.

        Blocks whose code would change, or that would merge into a neighbouring block, are
        left as they are and stay reported.
        """
        expected_style, tokens_to_fix = self._find_mismatched_blocks(document, config)

        if not tokens_to_fix:
            return None

        lines = document.content.split("\n")
        token_index = {id(token): index for index, token in enumerate(document.tokens)}
        list_item_starts = {
            token.map[0]
            for token in document.tokens
            if token.type == "list_item_open" and token.map is not None
        }

        # Process in reverse order to maintain correct line numbers
        for token in reversed(tokens_to_fix):
            start, end = token.map

            # A tab after a container marker can be partly consumed by it, so a rewritten
            # line could not reproduce the code's columns.
            if any("\t" in document.container_prefix(n) for n in range(start + 1, end + 1)):
                continue

            if expected_style == "fenced":
                replacement = self._to_fenced(document, token, start, end)
            else:
                replacement = self._to_indented(
                    document, token_index[id(token)], start, end, list_item_starts
                )

            if replacement is not None:
                lines[start:end] = replacement

        result = "\n".join(lines)
        if result == document.content:
            return None
        return result

    @staticmethod
    def _code_lines(token: Token) -> list[str]:
        return token.content.removesuffix("\n").split("\n")

    def _to_fenced(self, document: Document, token: Token, start: int, end: int) -> list[str]:
        """Wrap an indented code block in a fence, inside the same containers."""
        # The fence must be longer than any backtick run so no code line can close it.
        longest_run = max((len(run) for run in _BACKTICK_RUN.findall(token.content)), default=0)
        fence = "`" * max(3, longest_run + 1)

        # The first code line may carry a list marker; the opening fence takes it over.
        new_lines = [document.container_prefix(start + 1) + fence]
        for line_number, code in enumerate(self._code_lines(token), start=start + 1):
            if code:
                new_lines.append(document.continuation_prefix(line_number) + code)
            else:
                new_lines.append(document.blank_container_line(line_number))
        new_lines.append(document.continuation_prefix(end) + fence)
        return new_lines

    def _to_indented(
        self, document: Document, index: int, start: int, end: int, list_item_starts: set[int]
    ) -> list[str] | None:
        """Turn a fenced block into indented code, or return None if that changes the document.

        Indented code cannot interrupt a paragraph, cannot start or end with a blank line,
        continues a list item that precedes it, and merges with code blocks that are only
        separated from it by blank lines.
        """
        tokens = document.tokens
        code_lines = self._code_lines(tokens[index])

        if start in list_item_starts:
            return None  # removing the opening fence would remove the list marker
        if not code_lines[0].strip(" \t") or not code_lines[-1].strip(" \t"):
            return None
        if not is_blank_line(document.get_line(start) or ""):
            return None
        if not is_blank_line(document.get_line(end + 1) or ""):
            return None
        previous = self._previous_block(tokens, index)
        if previous is not None:
            if previous.type in _ABSORBING_PREVIOUS:
                return None
            if previous.type == "blockquote_open" and previous.map and previous.map[1] == start:
                # The line above is the quote's own ">" line, and an indented line starting
                # with ">" would continue that quote.
                return None
        following = self._next_block(tokens, index)
        if following is not None and following.type == "code_block":
            return None

        new_lines = []
        for line_number, code in enumerate(code_lines, start=start + 2):
            if not code:
                new_lines.append(document.blank_container_line(line_number))
                continue
            prefix = document.container_prefix(line_number)
            if prefix.endswith(">"):
                prefix += " "  # the marker's optional space would eat one indent column
            new_lines.append(prefix + "    " + code)
        return new_lines

    @staticmethod
    def _previous_block(tokens: list[Token], index: int) -> Token | None:
        """Return the opening token of the block before this one in the same container."""
        level = tokens[index].level
        for token in reversed(tokens[:index]):
            if token.level < level:
                return None
            # Tokens between a block's opening and closing tokens are nested deeper.
            if token.level == level and token.nesting != -1:
                return token
        return None

    @staticmethod
    def _next_block(tokens: list[Token], index: int) -> Token | None:
        """Return the opening token of the block after this one in the same container."""
        level = tokens[index].level
        for token in tokens[index + 1 :]:
            if token.level <= level:
                return token if token.level == level else None
        return None
