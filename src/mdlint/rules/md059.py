import re
from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD059Config(RuleConfig):
    """Configuration for MD059 rule."""

    prohibited_texts: list[str] = field(
        default_factory=lambda: ["click here", "here", "link", "more"],
        metadata={
            "description": "List of prohibited link text values.",
        },
    )


class MD059(Rule[MD059Config]):
    """Link text should be descriptive."""

    id = "MD059"
    name = "descriptive-link-text"
    summary = "Link text should be descriptive"
    config_class = MD059Config

    description = (
        'This rule is triggered when a link has generic text like "click here" '
        'or "link". Link text should be descriptive and communicate the purpose '
        'of the link (e.g., "Download document" or "Installation Guide"). '
        "This rule checks Markdown links only; HTML links are ignored."
    )

    rationale = (
        "Descriptive link text is especially important for screen readers which "
        "sometimes present links without context. Generic text like 'click here' "
        "or 'more' does not communicate what the link leads to."
    )

    example_valid = """\
# Descriptive Links

Download the [document](https://example.com/document.pdf).

See the [Installation Guide](./install.md) for details.
"""

    example_invalid = """\
# Non-Descriptive Links

For more information, [click here](https://example.com/).

See the documentation [here](https://docs.example.com/).

Visit this [link](https://example.com/page) for details.

Read [more](https://example.com/article).
"""

    # Pattern to match inline links: [text](destination)
    INLINE_LINK_PATTERN = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")

    # Pattern to match reference links: [text][ref] or [text][]
    REFERENCE_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\[([^\]]*)\]")

    # Pattern to match shortcut reference links: [text] (not followed by [ or ()
    SHORTCUT_LINK_PATTERN = re.compile(r"\[([^\]]+)\](?!\[|\()")

    def check(self, document: Document, config: MD059Config) -> list[Violation]:
        """Check for non-descriptive link text."""
        violations: list[Violation] = []

        # Normalize prohibited texts for comparison
        prohibited_set = {self._normalize(text) for text in config.prohibited_texts}

        if not prohibited_set:
            return violations

        # Build set of line numbers inside code blocks
        code_block_lines = self._get_code_block_lines(document)

        # Build map of inline code span columns per line
        code_span_positions = self._get_code_span_positions(document)

        # Parse reference definitions
        reference_definitions = self._get_reference_definitions(document)

        for line_num, line in enumerate(document.lines, start=1):
            # Skip lines in code blocks
            if line_num in code_block_lines:
                continue

            # Track positions that have been processed to avoid duplicates
            processed_ranges: list[tuple[int, int]] = []

            # Check inline links
            for match in self.INLINE_LINK_PATTERN.finditer(line):
                column = match.start() + 1

                # Check if this match is inside an inline code span
                if column in code_span_positions.get(line_num, set()):
                    continue

                # Track this range as processed
                processed_ranges.append((match.start(), match.end()))

                link_text = match.group(1)

                # Skip if link text contains inline code or HTML
                if "`" in link_text or "<" in link_text:
                    continue

                normalized_text = self._normalize(link_text)

                if normalized_text in prohibited_set:
                    violations.append(
                        Violation(
                            line=line_num,
                            column=column,
                            rule_id=self.id,
                            rule_name=self.name,
                            message=f"Non-descriptive link text: '{link_text}'",
                            context=document.get_line(line_num),
                        )
                    )

            # Check reference links [text][ref] and collapsed [text][]
            for match in self.REFERENCE_LINK_PATTERN.finditer(line):
                column = match.start() + 1

                # Check if this match is inside an inline code span
                if column in code_span_positions.get(line_num, set()):
                    continue

                # Track this range as processed
                processed_ranges.append((match.start(), match.end()))

                link_text = match.group(1)

                # Skip if link text contains inline code or HTML
                if "`" in link_text or "<" in link_text:
                    continue

                normalized_text = self._normalize(link_text)

                if normalized_text in prohibited_set:
                    violations.append(
                        Violation(
                            line=line_num,
                            column=column,
                            rule_id=self.id,
                            rule_name=self.name,
                            message=f"Non-descriptive link text: '{link_text}'",
                            context=document.get_line(line_num),
                        )
                    )

            # Check shortcut reference links [text]
            for match in self.SHORTCUT_LINK_PATTERN.finditer(line):
                # Check if this match overlaps with already processed ranges
                if self._overlaps_ranges(match.start(), match.end(), processed_ranges):
                    continue

                column = match.start() + 1

                # Check if this match is inside an inline code span
                if column in code_span_positions.get(line_num, set()):
                    continue

                # Skip if this is a reference definition line
                if self.REFERENCE_DEF_PATTERN.match(line):
                    continue

                link_text = match.group(1)
                ref_id_lower = link_text.lower()

                # Only check if reference definition exists
                if ref_id_lower not in reference_definitions:
                    continue

                # Skip if link text contains inline code or HTML
                if "`" in link_text or "<" in link_text:
                    continue

                normalized_text = self._normalize(link_text)

                if normalized_text in prohibited_set:
                    violations.append(
                        Violation(
                            line=line_num,
                            column=column,
                            rule_id=self.id,
                            rule_name=self.name,
                            message=f"Non-descriptive link text: '{link_text}'",
                            context=document.get_line(line_num),
                        )
                    )

        return violations

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text by removing punctuation and extra whitespace.

        Args:
            text: Text to normalize.

        Returns:
            Normalized lowercase text.
        """
        # Replace non-word characters and underscores with spaces
        normalized = re.sub(r"[\W_]+", " ", text)
        # Collapse multiple spaces and strip
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized.lower()
