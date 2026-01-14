import re
from dataclasses import dataclass, field

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD041Config(RuleConfig):
    """Configuration for MD041 rule."""

    level: int = field(
        default=1,
        metadata={
            "description": (
                "Heading level expected as the first heading (1-6). Default is 1 (h1). "
                "Values outside this range are treated as 1."
            ),
        },
    )
    front_matter_title: str = field(
        default=r"^\s*title\s*[:=]",
        metadata={
            "description": (
                "Regex pattern to match title in front matter. If front matter "
                "contains a matching line, the rule passes. Set to empty string to "
                "disable front matter title check."
            ),
        },
    )
    allow_preamble: bool = field(
        default=False,
        metadata={
            "description": (
                "Allow content before the first heading. When enabled, "
                "non-heading content before the first heading is ignored and "
                "only the first heading's level is checked."
            ),
        },
    )

    def __post_init__(self) -> None:
        if not 1 <= self.level <= 6:
            self.level = 1


class MD041(Rule[MD041Config]):
    """First line in a file should be a top-level heading."""

    id = "MD041"
    name = "first-line-heading"
    summary = "First line in a file should be a top-level heading"
    config_class = MD041Config

    HTML_HEADING_RE = re.compile(r"<(h[1-6])\b", re.IGNORECASE)

    description = (
        "This rule checks that the first line in a document is a top-level "
        "heading (h1 by default). The heading can be ATX-style (`# Title`), "
        "setext-style (underlined with `===`), or an HTML heading element "
        "(`<h1>Title</h1>`). Blank lines and HTML comments before the heading "
        "are allowed.\n\n"
        "If YAML or TOML front matter contains a title (matched by the "
        "`front_matter_title` regex pattern), the rule is satisfied without "
        "requiring a heading in the document body. Set `front_matter_title` "
        "to an empty string to disable this behavior.\n\n"
        "When `allow_preamble` is enabled, non-heading content before the "
        "first heading is permitted and only the heading's level is checked."
    )

    rationale = (
        "The top-level heading often acts as the title of a document. Having "
        "a clear title at the beginning helps readers understand the document's "
        "purpose and enables tools like static site generators to extract titles. "
        "Documents without a proper title heading may appear incomplete or "
        "confusing in navigation menus and search results."
    )

    example_valid = """\
# Document Title

This document starts with a top-level heading.
"""

    example_invalid = """\
This document does not start with a heading.

# Title Comes Too Late

The heading should be at the beginning.
"""

    def check(self, document: Document, config: MD041Config) -> list[Violation]:
        """Check for first-line-heading violations."""
        target_level = config.level

        # Check if front matter contains a title
        if config.front_matter_title and document.front_matter:
            if re.search(config.front_matter_title, document.front_matter, re.MULTILINE):
                return []

        # Find the first heading token, skipping front matter, blank lines,
        # and HTML comments. With allow_preamble, also skip non-heading content.
        for token in document.tokens:
            if token.type == "front_matter":
                continue
            if token.map is None:
                continue
            # Skip HTML comments (not real content)
            if token.type == "html_block" and token.content.lstrip().startswith("<!--"):
                continue

            line = token.map[0] + 1
            context = document.get_line(line)

            # ATX/setext headings
            if token.type == "heading_open":
                level = int(token.tag[1])
                if level == target_level:
                    return []
                return [
                    Violation(
                        line=line,
                        column=1,
                        rule_id=self.id,
                        rule_name=self.name,
                        message=f"First heading should be h{target_level}, found h{level}",
                        context=context,
                    )
                ]

            # HTML headings (<h1>, <h2>, etc.)
            if token.type == "html_block":
                match = self.HTML_HEADING_RE.search(token.content)
                if match:
                    html_level = int(match.group(1)[1])
                    if html_level == target_level:
                        return []
                    return [
                        Violation(
                            line=line,
                            column=1,
                            rule_id=self.id,
                            rule_name=self.name,
                            message=f"First heading should be h{target_level}, found h{html_level}",
                            context=context,
                        )
                    ]

            # Non-heading content
            if not config.allow_preamble:
                return [
                    Violation(
                        line=line,
                        column=1,
                        rule_id=self.id,
                        rule_name=self.name,
                        message=f"First line should be a top-level h{target_level} heading",
                        context=context,
                    )
                ]

        return []
