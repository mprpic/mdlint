import re
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass, field
from urllib.parse import unquote

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD051Config(RuleConfig):
    """Configuration for MD051 rule."""

    ignore_case: bool = field(
        default=False,
        metadata={
            "description": "Ignore case when comparing fragments with headings.",
        },
    )
    ignored_pattern: str = field(
        default="",
        metadata={
            "description": "Regular expression pattern for fragments to ignore.",
        },
    )


class MD051(Rule[MD051Config]):
    """Link fragments should be valid."""

    id = "MD051"
    name = "link-fragments"
    summary = "Link fragments should be valid"
    config_class = MD051Config

    description = (
        "This rule checks that link fragments (internal links starting with `#`) "
        "reference valid anchors in the document. Valid anchors include headings "
        "(converted to fragments using when Markdown is displayed on GitHub), HTML elements with "
        "`id` attributes, and `<a>` elements with `name` attributes."
    )

    rationale = (
        "GitHub section links are created automatically for every heading when "
        "Markdown content is displayed. However, section links break if headings "
        "are renamed or removed. This rule helps identify broken section links "
        "within a document before they cause problems for readers."
    )

    example_valid = """\
# Heading One

This [link](#heading-one) is valid.

## Heading Two

This [link](#heading-two) is also valid.

A [link to top](#top) is always valid.

<a id="custom-anchor"></a>

This [link](#custom-anchor) references an HTML anchor.
"""

    example_invalid = """\
# Heading One

This [link](#non-existent) references a non-existent heading.

## Heading Two

Another [bad link](#missing-section) here.
"""

    # Pattern to match inline links: [text](destination)
    INLINE_LINK_PATTERN = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")

    # Pattern to match HTML id attribute
    HTML_ID_PATTERN = re.compile(r'id\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)

    # Pattern to match HTML name attribute (for <a> tags)
    HTML_NAME_PATTERN = re.compile(r'name\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)

    # Pattern to match opening HTML tags
    HTML_TAG_PATTERN = re.compile(r"<\s*([a-zA-Z][a-zA-Z0-9]*)\s*([^>]*)>", re.IGNORECASE)

    # Pattern to match custom anchor syntax {#anchor-name} in headings
    CUSTOM_ANCHOR_PATTERN = re.compile(r"\{(#[a-z\d]+(?:[-_][a-z\d]+)*)\}")

    # Pattern to match GitHub line fragment syntax
    LINE_FRAGMENT_PATTERN = re.compile(r"^#(?:L\d+(?:C\d+)?(?:-L\d+(?:C\d+)?)?|L\d+)$")

    # Characters that need URL-encoding in fragments
    _UNSAFE_FRAGMENT_RE = re.compile(r"[^a-zA-Z0-9._-]")

    def _find_fragment_links(
        self, document: Document, config: MD051Config
    ) -> Iterator[tuple[int, int, re.Match[str], str, str | None]]:
        """Yield fragment link matches with metadata.

        Yields tuples of (line_num, column, match, destination, matching_key).
        matching_key is the correctly-cased fragment for case mismatches, or None
        if the fragment is valid or not found at all.
        """
        code_block_lines = document.code_block_lines
        fragments = self._collect_fragments(document, code_block_lines)
        fragments_lower: dict[str, str] = {k.lower(): k for k in fragments}
        code_span_positions = document.code_span_positions

        ignored_pattern_re = None
        if config.ignored_pattern:
            ignored_pattern_re = re.compile(config.ignored_pattern)

        for line_num, line in enumerate(document.lines, start=1):
            if line_num in code_block_lines:
                continue

            for match in self.INLINE_LINK_PATTERN.finditer(line):
                column = match.start() + 1
                if column in code_span_positions.get(line_num, set()):
                    continue

                destination = match.group(2).strip()
                result = self._classify_fragment(
                    destination, fragments, fragments_lower, config, ignored_pattern_re
                )
                if result is not None:
                    yield line_num, column, match, destination, result

            ref_match = Document.REFERENCE_DEF_PATTERN.match(line)
            if ref_match:
                destination = ref_match.group(2).strip()
                dest_start = line.find(destination)
                column = dest_start + 1 if dest_start >= 0 else 1
                result = self._classify_fragment(
                    destination, fragments, fragments_lower, config, ignored_pattern_re
                )
                if result is not None:
                    yield line_num, column, ref_match, destination, result

    def _classify_fragment(
        self,
        destination: str,
        fragments: dict[str, int],
        fragments_lower: dict[str, str],
        config: MD051Config,
        ignored_pattern_re: re.Pattern | None,
    ) -> str | None:
        """Classify a fragment link destination.

        Returns:
            - None if the fragment is valid or should be skipped (not a violation).
            - The correctly-cased fragment string for case mismatches.
            - Empty string "" if the fragment is not found at all.
        """
        if not destination.startswith("#") or len(destination) <= 1:
            return None
        if self.LINE_FRAGMENT_PATTERN.match(destination):
            return None

        fragment_text = destination[1:]
        if ignored_pattern_re and ignored_pattern_re.search(fragment_text):
            return None

        decoded_fragment = unquote(fragment_text)
        encoded_destination = "#" + self._encode_fragment(decoded_fragment)

        if encoded_destination in fragments:
            return None

        matching_key = fragments_lower.get(destination.lower())
        if matching_key:
            if config.ignore_case:
                return None
            return matching_key

        return ""

    def check(self, document: Document, config: MD051Config) -> list[Violation]:
        """Check for invalid link fragment violations."""
        violations: list[Violation] = []

        for line_num, column, _, destination, matching_key in self._find_fragment_links(
            document, config
        ):
            if matching_key:
                message = f"Expected: {matching_key}; Actual: {destination}"
            else:
                message = f"Link fragment {destination} not found in document"

            violations.append(
                Violation(
                    line=line_num,
                    column=column,
                    rule_id=self.id,
                    rule_name=self.name,
                    message=message,
                    context=document.get_line(line_num),
                )
            )

        return violations

    def fix(self, document: Document, config: MD051Config) -> str | None:
        """Fix case-mismatch link fragments by replacing with the correct casing.

        Only fixes fragments that exist in the document but with different casing.
        Non-existent fragments are left unchanged since intent cannot be determined.
        """
        replacements_by_line: dict[int, list[tuple[re.Match[str], str]]] = {}

        for line_num, _, match, _, matching_key in self._find_fragment_links(document, config):
            if matching_key:
                replacements_by_line.setdefault(line_num, []).append((match, matching_key))

        if not replacements_by_line:
            return None

        lines = document.content.split("\n")
        for line_num, line_replacements in replacements_by_line.items():
            line = lines[line_num - 1]
            for match, new_dest in reversed(line_replacements):
                start = match.start(2)
                end = match.end(2)
                line = line[:start] + new_dest + line[end:]
            lines[line_num - 1] = line

        return "\n".join(lines)

    def _collect_fragments(self, document: Document, code_block_lines: set[int]) -> dict[str, int]:
        """Collect all valid fragments from the document.

        Returns:
            Dict mapping fragment strings (with #) to occurrence count.
        """
        fragments: dict[str, int] = {"#top": 0}

        # Collect fragments from headings
        tokens = document.tokens
        for i, token in enumerate(tokens):
            if token.type == "heading_open" and token.map:
                # The inline token immediately follows heading_open
                if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                    heading_text = self._extract_heading_text(tokens[i + 1])
                    if heading_text:
                        fragment = self._heading_to_fragment(heading_text)
                        if fragment != "#":
                            count = fragments.get(fragment, 0)
                            if count:
                                fragments[f"{fragment}-{count}"] = 0
                            fragments[fragment] = count + 1

                        # Check for custom anchor syntax
                        for match in self.CUSTOM_ANCHOR_PATTERN.finditer(heading_text):
                            anchor = match.group(1)
                            if anchor not in fragments:
                                fragments[anchor] = 1

        # Collect fragments from HTML anchors (skip code blocks)
        for line_num, line in enumerate(document.lines, start=1):
            if line_num in code_block_lines:
                continue
            for tag_match in self.HTML_TAG_PATTERN.finditer(line):
                tag_name = tag_match.group(1).lower()
                attrs = tag_match.group(2)

                # Check for id attribute on any tag
                id_match = self.HTML_ID_PATTERN.search(attrs)
                if id_match:
                    fragments[f"#{id_match.group(1)}"] = 0

                # Check for name attribute on <a> tags
                if tag_name == "a":
                    name_match = self.HTML_NAME_PATTERN.search(attrs)
                    if name_match:
                        fragments[f"#{name_match.group(1)}"] = 0

        return fragments

    @staticmethod
    def _extract_heading_text(inline_token) -> str:
        """Extract text content from a heading's inline token.

        Includes text and code_inline content. Excludes image alt text
        to match the GitHub heading algorithm.
        """
        if not inline_token.children:
            return ""

        parts = []
        for child in inline_token.children:
            if child.type == "image":
                continue
            if child.type in ("text", "code_inline") and child.content:
                parts.append(child.content)
        return "".join(parts)

    def _heading_to_fragment(self, heading_text: str) -> str:
        """Convert heading text to a fragment using the GitHub algorithm.

        The algorithm:
        1. Convert to lowercase
        2. Remove punctuation (keep letters, marks, numbers, connector punctuation)
        3. Convert spaces to dashes
        4. URL-encode the result

        Args:
            heading_text: The heading text.

        Returns:
            The fragment string with leading #.
        """
        # Remove custom anchor syntax from heading text
        text = self.CUSTOM_ANCHOR_PATTERN.sub("", heading_text).strip()

        # Convert to lowercase
        text = text.lower()

        # Remove characters that are not in allowed Unicode categories
        # Allowed: Letter, Mark, Number, Connector_Punctuation, dash, space
        result = []
        for char in text:
            category = unicodedata.category(char)
            if category.startswith(("L", "M", "N")) or category == "Pc":
                result.append(char)
            elif char == "-":
                result.append(char)
            elif char == " " or category == "Zs":
                result.append(" ")
            # Other characters are removed

        text = "".join(result)

        # Convert spaces to dashes
        text = text.replace(" ", "-")

        return "#" + self._encode_fragment(text)

    @classmethod
    def _encode_fragment(cls, text: str) -> str:
        """URL-encode a fragment, similar to encodeURIComponent.

        Args:
            text: The fragment text (without #).

        Returns:
            URL-encoded fragment.
        """
        return cls._UNSAFE_FRAGMENT_RE.sub(
            lambda m: "".join(f"%{b:02X}" for b in m.group().encode("utf-8")), text
        )
