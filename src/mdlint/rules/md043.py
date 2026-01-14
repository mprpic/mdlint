from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD043Config(RuleConfig):
    """Configuration for MD043 rule."""

    headings: list[str] = field(
        default_factory=list,
        metadata={
            "description": (
                "List of required headings in the format `## Heading Text`. Use `*` "
                "for zero or more unspecified headings, `+` for one or more "
                "unspecified headings, and `?` for exactly one unspecified heading."
            ),
        },
    )
    match_case: bool = field(
        default=False,
        metadata={
            "description": "When True, heading text must match case exactly.",
        },
    )


class MD043(Rule[MD043Config]):
    """Required heading structure."""

    id = "MD043"
    name = "required-headings"
    summary = "Required heading structure"
    config_class = MD043Config

    description = (
        "This rule checks that the headings in a document match a required structure. "
        "Use special wildcards in the headings configuration: `*` for zero or more "
        "unspecified headings, `+` for one or more unspecified headings, and `?` "
        "for exactly one unspecified heading.\n\n"
        "For example, to require a document to follow to include headings `# Document Title`, "
        "`## Description`, `### Examples`, and no other headings, the `headings` configuration "
        "option would be set to an ordered list of:\n\n"
        "```\n"
        'headings = ["# Document Title", "## Description", "### Examples"]\n'
        "```"
    )

    rationale = (
        "Projects may wish to enforce a consistent document structure across a set "
        "of similar content. This ensures that all documents follow the same heading "
        "hierarchy and organization."
    )

    example_valid = """\
# Document Title

## Description

This section describes the document.

## Examples

Some examples here.
"""

    example_invalid = """\
# Document Title

## Introduction

This section has the wrong name.

## Examples

Some examples here.
"""

    def check(self, document: Document, config: MD043Config) -> list[Violation]:
        """Check for required heading structure violations."""
        violations: list[Violation] = []

        required_headings = config.headings
        if not required_headings:
            # Nothing to check
            return violations

        # Get all headings from the document
        doc_headings = self._get_document_headings(document)

        # Track position in required headings
        req_idx = 0
        doc_idx = 0
        match_any = False
        has_error = False

        def handle_case(s: str) -> str:
            return s if config.match_case else s.lower()

        def get_expected() -> str:
            nonlocal req_idx
            if req_idx < len(required_headings):
                result = required_headings[req_idx]
                req_idx += 1
                return result
            return "[None]"

        while doc_idx < len(doc_headings) and not has_error:
            actual_text, actual_line = doc_headings[doc_idx]
            expected = get_expected()

            if expected == "*":
                # Zero or more unspecified headings
                next_expected = get_expected()
                if handle_case(next_expected) != handle_case(actual_text):
                    # Current heading doesn't match next required, so it's part of "*"
                    match_any = True
                    req_idx -= 1  # Stay at this position for next heading
                else:
                    # Current heading matches the one after "*"
                    match_any = False
                doc_idx += 1
            elif expected == "+":
                # One or more unspecified headings
                match_any = True
                doc_idx += 1
            elif expected == "?":
                # Exactly one unspecified heading - allow current, match next
                doc_idx += 1
            elif handle_case(expected) == handle_case(actual_text):
                # Exact match
                match_any = False
                doc_idx += 1
            elif match_any:
                # In a wildcard section, keep consuming
                req_idx -= 1
                doc_idx += 1
            else:
                # Mismatch
                violations.append(
                    Violation(
                        line=actual_line,
                        column=1,
                        rule_id=self.id,
                        rule_name=self.name,
                        message=f"Expected: {expected}, Actual: {actual_text}",
                        context=document.get_line(actual_line),
                    )
                )
                has_error = True

        # Check for missing required headings at the end
        if not has_error:
            extra_required = len(required_headings) - req_idx
            if (
                extra_required > 1 or (extra_required == 1 and required_headings[req_idx] != "*")
            ) and (doc_headings or not all(h == "*" for h in required_headings)):
                last_line = len(document.lines)
                violations.append(
                    Violation(
                        line=last_line,
                        column=1,
                        rule_id=self.id,
                        rule_name=self.name,
                        message=f"Missing required heading: {required_headings[req_idx]}",
                        context=document.get_line(last_line),
                    )
                )

        return violations

    @staticmethod
    def _get_document_headings(document: Document) -> list[tuple[str, int]]:
        """Extract all headings from the document with their formatted text and line.

        Returns:
            List of tuples containing (formatted_heading, line_number).
            Formatted heading is in the format "## Heading Text".
        """
        headings: list[tuple[str, int]] = []

        tokens = document.tokens
        for i, token in enumerate(tokens):
            if token.type == "heading_open":
                level = int(token.tag[1])
                line = token.map[0] + 1 if token.map else 1

                # Get heading text from the inline token that follows heading_open
                if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                    text = tokens[i + 1].content
                    formatted = f"{'#' * level} {text}"
                    headings.append((formatted, line))

        return headings
