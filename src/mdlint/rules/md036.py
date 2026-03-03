from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD036Config(RuleConfig):
    """Configuration for MD036 rule."""

    punctuation: str = field(
        default=".,;:!?",
        metadata={
            "description": "Characters considered as trailing punctuation.",
        },
    )


class MD036(Rule[MD036Config]):
    """Emphasis used instead of a heading."""

    id = "MD036"
    name = "no-emphasis-as-heading"
    summary = "Emphasis used instead of a heading"
    config_class = MD036Config

    description = (
        "This rule checks for paragraphs that consist entirely of bold or italic "
        "text, which may indicate the author is using emphasis instead of a proper "
        "heading. Paragraphs that end with punctuation are not flagged, as they are "
        "likely intended to be emphasized sentences rather than headings."
    )

    rationale = (
        "Using emphasis instead of a heading prevents tools from inferring the "
        "structure of a document. Proper headings enable document parsing, "
        "navigation, and accessibility features that emphasized text cannot provide."
    )

    example_valid = """\
# Proper Heading

This is a paragraph with **bold text** in it.

Another paragraph with *italic text* and more words.

**This line ends with punctuation.**

_This also ends with punctuation:_

Some text with **emphasis** that is not the whole paragraph.
"""

    example_invalid = """\
# Proper Heading

**This is used as a heading**

Some text under the emphasis heading.

_Another emphasis heading_

More text here.

***Bold and italic heading***
"""

    def check(self, document: Document, config: MD036Config) -> list[Violation]:
        """Check for emphasis used instead of a heading."""
        violations: list[Violation] = []

        for i, token in enumerate(document.tokens):
            # Look for top-level paragraph_open tokens only; emphasis
            # inside list items, blockquotes, etc. can't be headings.
            if token.type == "paragraph_open" and token.map and token.level == 0:
                line_start = token.map[0] + 1
                line_end = token.map[1]

                # Only check single-line paragraphs
                if line_end - line_start > 1:
                    continue

                # Get the inline token that follows paragraph_open
                if i + 1 < len(document.tokens):
                    inline_token = document.tokens[i + 1]
                    if inline_token.type == "inline" and inline_token.children:
                        if self._is_emphasis_only_paragraph(
                            inline_token.children, config.punctuation
                        ):
                            line_content = document.get_line(line_start)
                            violations.append(
                                Violation(
                                    line=line_start,
                                    column=1,
                                    rule_id=self.id,
                                    rule_name=self.name,
                                    message="Emphasis used instead of a heading",
                                    context=line_content,
                                )
                            )

        return violations

    @staticmethod
    def _is_emphasis_only_paragraph(children: list, punctuation: str) -> bool:
        """Check if inline children represent emphasis-only content.

        A paragraph is emphasis-only if:
        1. It contains only emphasis tokens (em or strong) with text inside
        2. The text does not end with punctuation (unless punctuation is empty)
        3. It is a single-line paragraph (no softbreaks)

        Args:
            children: List of inline token children.
            punctuation: Characters to consider as trailing punctuation.

        Returns:
            True if this is an emphasis-only paragraph that should be flagged.
        """
        if not children:
            return False

        # Check for softbreak tokens which indicate multi-line content
        if any(c.type == "softbreak" for c in children):
            return False

        # Check if the structure is: em_open/strong_open, text, em_close/strong_close
        # or nested emphasis like: strong_open, em_open, text, em_close, strong_close
        emphasis_open = {"em_open", "strong_open"}
        emphasis_close = {"em_close", "strong_close"}

        # All tokens must be either emphasis markers or text, and all
        # non-empty text must be inside emphasis markers. Only a single
        # top-level emphasis block is allowed (e.g. **a** **b** is not
        # flagged because it has two separate emphasis blocks).
        text_content = ""
        top_level_emphasis_count = 0
        depth = 0

        for child in children:
            if child.type in emphasis_open:
                if depth == 0:
                    top_level_emphasis_count += 1
                depth += 1
            elif child.type in emphasis_close:
                depth -= 1
            elif child.type == "text":
                if depth == 0 and child.content.strip():
                    # Non-empty text outside emphasis markers
                    return False
                text_content += child.content
            else:
                # Found something other than emphasis or text
                return False

        if top_level_emphasis_count != 1:
            return False

        if not text_content:
            return False

        # Check if the paragraph ends with punctuation
        text_content = text_content.strip()
        if text_content and punctuation and text_content[-1] in punctuation:
            return False

        return True
