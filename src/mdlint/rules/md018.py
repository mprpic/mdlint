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

    def _find_missing_space_lines(self, document: Document) -> list[tuple[int, re.Match[str]]]:
        """Return list of (line_num, match) for lines missing space after hash."""
        ignored_lines = document.code_block_lines | document.html_block_lines

        results: list[tuple[int, re.Match[str]]] = []
        for line_num, line in enumerate(document.lines, start=1):
            if line_num in ignored_lines:
                continue

            match = self.ATX_MISSING_SPACE_PATTERN.match(line)
            if match:
                results.append((line_num, match))

        return results

    def check(self, document: Document, config: MD018Config) -> list[Violation]:
        """Check for missing space after hash in atx headings."""
        violations: list[Violation] = []

        for line_num, _ in self._find_missing_space_lines(document):
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

    def fix(self, document: Document, config: MD018Config) -> str | None:
        """Fix missing space after hash in atx headings by inserting a space."""
        matching_lines = self._find_missing_space_lines(document)
        if not matching_lines:
            return None

        lines = document.content.split("\n")
        for line_num, match in matching_lines:
            hashes = match.group(1)
            rest = lines[line_num - 1][match.end(1) :]
            lines[line_num - 1] = hashes + " " + rest

        return "\n".join(lines)
