import re
from dataclasses import dataclass

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD045Config(RuleConfig):
    """Configuration for MD045 rule."""


class MD045(Rule[MD045Config]):
    """Images should have alternate text (alt text)."""

    id = "MD045"
    name = "no-alt-text"
    summary = "Images should have alternate text (alt text)"
    config_class = MD045Config

    description = (
        "This rule is triggered when an image is missing alternate text (alt text) "
        "information. Images with whitespace-only alt text (e.g. `![ ](image.jpg)`) "
        "are also considered to be missing alt text. "
        "Alternate text can be specified inline as `![Alt text](image.jpg)`, "
        "with reference syntax as `![Alt text][ref]`, or with HTML as "
        '`<img src="image.jpg" alt="Alt text" />`.'
    )

    rationale = (
        "Alternate text is important for accessibility and describes the content of "
        "an image for people who may not be able to see it. Screen readers use alt "
        "text to describe images to visually impaired users."
    )

    example_valid = """\
# Images with Alt Text

![A descriptive alt text](image.png)

Reference style image:

![Another alt text][ref]

[ref]: image.jpg "Optional title"

HTML image with alt attribute:

<img src="image.png" alt="Alt text for HTML image" />

HTML image hidden from assistive technology:

<img src="decorative.png" aria-hidden="true" />
"""

    example_invalid = """\
# Images without Alt Text

![](image.png)

Reference style image without alt:

![][ref]

[ref]: image.jpg

HTML image without alt attribute:

<img src="image.png" />
"""

    # Pattern to match markdown images: ![alt](url) or ![alt][ref]
    # Captures: (1) alt text, (2) closing bracket + rest
    MARKDOWN_IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\](\([^)]*\)|\[[^\]]*\])")

    # Pattern to match HTML img tags
    # Matches: <img ...> or <img ... />
    HTML_IMG_PATTERN = re.compile(r"<\s*img\s+[^>]*?>", re.IGNORECASE)

    # Pattern to match alt attribute in HTML
    # Matches: alt="value", alt='value', or alt=value
    ALT_ATTR_PATTERN = re.compile(r'\balt\s*=\s*(?:"[^"]*"|\'[^\']*\'|\S+)', re.IGNORECASE)

    # Pattern to match aria-hidden="true" attribute
    ARIA_HIDDEN_PATTERN = re.compile(r'\baria-hidden\s*=\s*["\']?true["\']?', re.IGNORECASE)

    def check(self, document: Document, config: MD045Config) -> list[Violation]:
        """Check for images without alt text."""
        violations: list[Violation] = []

        # Get lines that are inside code blocks
        code_block_lines = self._get_code_block_lines(document)

        # Get inline code span columns per line
        code_span_positions = self._get_code_span_positions(document)

        for line_num, line in enumerate(document.lines, start=1):
            # Skip lines in code blocks
            if line_num in code_block_lines:
                continue

            # Check markdown images
            violations.extend(
                self._check_markdown_images(
                    line, line_num, document, code_span_positions.get(line_num, set())
                )
            )

            # Check HTML img tags
            violations.extend(
                self._check_html_images(
                    line, line_num, document, code_span_positions.get(line_num, set())
                )
            )

        return violations

    def _check_markdown_images(
        self,
        line: str,
        line_num: int,
        document: Document,
        code_columns: set[int],
    ) -> list[Violation]:
        """Check markdown images for missing alt text."""
        violations: list[Violation] = []

        for match in self.MARKDOWN_IMAGE_PATTERN.finditer(line):
            alt_text = match.group(1)
            column = match.start() + 1  # 1-indexed

            # Skip if inside inline code
            if column in code_columns:
                continue

            # Check if alt text is empty or whitespace only
            if not alt_text.strip():
                violations.append(
                    Violation(
                        line=line_num,
                        column=column,
                        rule_id=self.id,
                        rule_name=self.name,
                        message="Image is missing alternate text",
                        context=document.get_line(line_num),
                    )
                )

        return violations

    def _check_html_images(
        self,
        line: str,
        line_num: int,
        document: Document,
        code_columns: set[int],
    ) -> list[Violation]:
        """Check HTML img tags for missing alt attribute."""
        violations: list[Violation] = []

        for match in self.HTML_IMG_PATTERN.finditer(line):
            img_tag = match.group(0)
            column = match.start() + 1  # 1-indexed

            # Skip if inside inline code
            if column in code_columns:
                continue

            # Skip if aria-hidden="true" is present
            if self.ARIA_HIDDEN_PATTERN.search(img_tag):
                continue

            # Check if alt attribute is present
            if not self.ALT_ATTR_PATTERN.search(img_tag):
                violations.append(
                    Violation(
                        line=line_num,
                        column=column,
                        rule_id=self.id,
                        rule_name=self.name,
                        message="HTML image is missing alt attribute",
                        context=document.get_line(line_num),
                    )
                )

        return violations
