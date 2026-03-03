import re
from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD054Config(RuleConfig):
    """Configuration for MD054 rule."""

    autolink: bool = field(
        default=True,
        metadata={
            "description": "Allow autolinks (e.g., `<https://example.com>`).",
        },
    )
    inline: bool = field(
        default=True,
        metadata={
            "description": "Allow inline links and images.",
        },
    )
    full: bool = field(
        default=True,
        metadata={
            "description": "Allow full reference links and images (e.g., `[text][ref]`).",
        },
    )
    collapsed: bool = field(
        default=True,
        metadata={
            "description": "Allow collapsed reference links and images (e.g., `[ref][]`).",
        },
    )
    shortcut: bool = field(
        default=True,
        metadata={
            "description": "Allow shortcut reference links and images (e.g., `[ref]`).",
        },
    )
    url_inline: bool = field(
        default=True,
        metadata={
            "description": "Allow URLs as inline links (e.g., `[https://...](https://...)`).",
        },
    )


class MD054(Rule[MD054Config]):
    """Link and image style."""

    id = "MD054"
    name = "link-image-style"
    summary = "Link and image style"
    config_class = MD054Config

    description = (
        "This rule checks that links and images in Markdown follow a consistent "
        "style. Links and images can use inline syntax, reference syntax (full, "
        "collapsed, or shortcut), or autolink syntax. The rule can be configured "
        "to allow or disallow specific styles."
    )

    rationale = (
        "Consistent formatting makes it easier to understand a document. "
        "Autolinks are concise but appear as raw URLs. Inline links include "
        "descriptive text but take more space. Reference links are easier to "
        "read in Markdown source but require separate definitions."
    )

    example_valid = """\
# Valid Link Styles

This document uses inline links [like this](https://example.com).

Here is an ![inline image](https://example.com/image.png).

Reference links [like this][ref] are also used.

[ref]: https://example.com
"""

    example_invalid = """\
# Invalid Link Style

<https://example.com>

[inline link](https://example.com)
"""

    # Pattern to match autolinks: <url> or <email>
    AUTOLINK_PATTERN = re.compile(r"<((?:https?|ftp)://[^>\s]+|[^@>\s]+@[^@>\s]+\.[^@>\s]+)>")

    # Pattern to match inline links/images: [text](url) or ![alt](url)
    # Supports one level of balanced parentheses in URLs (e.g. Wikipedia links)
    INLINE_LINK_PATTERN = re.compile(r"(!?)\[([^\]]*)\]\(((?:[^()]*|\([^()]*\))*)\)")

    # Pattern to match full reference links/images: [text][ref]
    FULL_REFERENCE_PATTERN = re.compile(r"(!?)\[([^\]]+)\]\[([^\]]+)\]")

    # Pattern to match collapsed reference links/images: [ref][]
    COLLAPSED_REFERENCE_PATTERN = re.compile(r"(!?)\[([^\]]+)\]\[\]")

    # Pattern to match shortcut reference links/images: [ref] (not followed by [ or ()
    SHORTCUT_REFERENCE_PATTERN = re.compile(r"(!?)\[([^\]]+)\](?!\[|\()")

    def check(self, document: Document, config: MD054Config) -> list[Violation]:
        """Check for link and image style violations."""
        violations: list[Violation] = []

        # If all styles are allowed, nothing to check
        if (
            config.autolink
            and config.inline
            and config.full
            and config.collapsed
            and config.shortcut
            and config.url_inline
        ):
            return violations

        # Build set of line numbers inside code blocks
        code_block_lines = self._get_code_block_lines(document)

        # Build map of inline code span columns per line
        code_span_positions = self._get_code_span_positions(document)

        # Parse reference definitions for resolving shortcuts
        reference_definitions = self._get_reference_definitions(document)

        for line_num, line in enumerate(document.lines, start=1):
            # Skip lines in code blocks
            if line_num in code_block_lines:
                continue

            # Skip reference definition lines
            if self.REFERENCE_DEF_PATTERN.match(line):
                continue

            # Track processed ranges to avoid duplicate reports
            processed_ranges: list[tuple[int, int]] = []

            # Check autolinks
            if not config.autolink:
                for match in self.AUTOLINK_PATTERN.finditer(line):
                    column = match.start() + 1

                    # Check if inside inline code
                    if column in code_span_positions.get(line_num, set()):
                        continue

                    processed_ranges.append((match.start(), match.end()))
                    violations.append(
                        Violation(
                            line=line_num,
                            column=column,
                            rule_id=self.id,
                            rule_name=self.name,
                            message="Autolink style not allowed",
                            context=document.get_line(line_num),
                        )
                    )

            # Check inline links and images
            for match in self.INLINE_LINK_PATTERN.finditer(line):
                column = match.start() + 1

                # Check if inside inline code
                if column in code_span_positions.get(line_num, set()):
                    continue

                # Check if already processed
                if self._overlaps_ranges(match.start(), match.end(), processed_ranges):
                    continue

                processed_ranges.append((match.start(), match.end()))

                is_image = match.group(1) == "!"
                label = match.group(2)
                destination = match.group(3).strip()

                # Check url_inline: URL as inline link text (only for links, not images).
                # Only flag when autolinks are allowed, since the suggestion is to
                # convert to autolink syntax.
                if not config.url_inline and config.autolink and not is_image:
                    if label == destination and self._is_autolinkable(destination):
                        violations.append(
                            Violation(
                                line=line_num,
                                column=column,
                                rule_id=self.id,
                                rule_name=self.name,
                                message="URL inline link can be converted to autolink",
                                context=document.get_line(line_num),
                            )
                        )
                        continue

                # Check inline style
                if not config.inline:
                    link_type = "image" if is_image else "link"
                    violations.append(
                        Violation(
                            line=line_num,
                            column=column,
                            rule_id=self.id,
                            rule_name=self.name,
                            message=f"Inline {link_type} style not allowed",
                            context=document.get_line(line_num),
                        )
                    )

            # Check reference-style links/images (full, collapsed, shortcut)
            # Each entry: (allowed, pattern, ref_id_group, style_name)
            ref_checks: list[tuple[bool, re.Pattern, int, str]] = [
                (config.full, self.FULL_REFERENCE_PATTERN, 3, "Full reference"),
                (config.collapsed, self.COLLAPSED_REFERENCE_PATTERN, 2, "Collapsed reference"),
                (config.shortcut, self.SHORTCUT_REFERENCE_PATTERN, 2, "Shortcut reference"),
            ]
            for allowed, pattern, ref_group, style_name in ref_checks:
                if allowed:
                    continue
                for match in pattern.finditer(line):
                    column = match.start() + 1

                    if column in code_span_positions.get(line_num, set()):
                        continue

                    if self._overlaps_ranges(match.start(), match.end(), processed_ranges):
                        continue

                    processed_ranges.append((match.start(), match.end()))

                    is_image = match.group(1) == "!"
                    ref_id = match.group(ref_group).lower()

                    # Only report if reference definition exists
                    if ref_id in reference_definitions:
                        link_type = "image" if is_image else "link"
                        violations.append(
                            Violation(
                                line=line_num,
                                column=column,
                                rule_id=self.id,
                                rule_name=self.name,
                                message=f"{style_name} {link_type} style not allowed",
                                context=document.get_line(line_num),
                            )
                        )

        return violations

    @staticmethod
    def _is_autolinkable(url: str) -> bool:
        """Check if a URL can be converted to an autolink."""
        # Check if it's an absolute URL
        if not url.startswith(("http://", "https://", "ftp://")):
            return False

        # Check for disallowed characters
        if " " in url or "<" in url or ">" in url:
            return False

        return True
