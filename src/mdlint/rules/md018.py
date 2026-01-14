import re
from dataclasses import dataclass

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD018Config(RuleConfig):
    """Configuration for MD018 rule."""


class MD018(Rule[MD018Config]):
    """No space after hash on atx style heading."""

    id = "MD018"
    name = "no-missing-space-atx"
    summary = "No space after hash on atx style heading"
    config_class = MD018Config

    description = (
        "This rule checks that ATX-style headings have a space between the "
        "hash characters (`#`) and the heading text. For example, `# Heading` "
        "is correct, but `#Heading` is not."
    )

    rationale = (
        "Missing a space after the hash characters in an ATX-style heading "
        "can cause the heading to be improperly rendered. Some Markdown parsers "
        "require a space after the hash to recognize the line as a heading."
    )

    example_valid = """\
# Heading 1

## Heading 2

### Heading 3
"""

    example_invalid = """\
#Heading 1

##Heading 2

###Heading 3
"""

    # Pattern to match lines starting with hash(es) followed by non-space, non-hash char
    ATX_MISSING_SPACE_PATTERN = re.compile(r"^(#+)[^#\s]")

    def check(self, document: Document, config: MD018Config) -> list[Violation]:
        """Check for missing space after hash in atx headings."""
        violations: list[Violation] = []

        # Build set of line numbers inside code blocks or HTML blocks
        ignored_lines = self._get_code_block_lines(document)
        for token in document.tokens:
            if token.type == "html_block" and token.map:
                for line_num in range(token.map[0] + 1, token.map[1] + 1):
                    ignored_lines.add(line_num)

        for line_num, line in enumerate(document.lines, start=1):
            # Skip lines inside code blocks or HTML blocks
            if line_num in ignored_lines:
                continue

            # Check if line matches the missing space pattern
            match = self.ATX_MISSING_SPACE_PATTERN.match(line)
            if match:
                violations.append(
                    Violation(
                        line=line_num,
                        column=1,
                        rule_id=self.id,
                        rule_name=self.name,
                        message="No space after hash on atx style heading",
                        context=document.get_line(line_num),
                    )
                )

        return violations
