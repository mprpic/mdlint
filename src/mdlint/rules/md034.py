import bisect
import re
from collections.abc import Iterator
from dataclasses import dataclass

from mdlint.document import Document
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


@dataclass
class MD034Config(RuleConfig):
    """Configuration for MD034 rule."""


class MD034(Rule[MD034Config]):
    """Bare URL used."""

    id = "MD034"
    name = "no-bare-urls"
    summary = "Bare URL used"
    config_class = MD034Config

    description = (
        "This rule is triggered when a URL or email address appears in the "
        "document without being enclosed in angle brackets, link syntax, or "
        "code spans. URLs using `http`, `https`, and `ftp` protocols are checked, "
        "as are email addresses with or without a `mailto:` scheme.\n\n"
        "Text that is not rendered as Markdown (front matter, HTML blocks, HTML "
        "tag attributes, Hugo shortcodes, and reference definitions) is ignored, "
        "as are URLs that are already part of a link's text or an `<a>` element."
    )

    rationale = (
        "Without angle brackets, a bare URL or email address is not converted "
        "into a clickable link by some Markdown parsers. Wrapping URLs in "
        "angle brackets (`<url>`) or using proper link syntax ensures consistent "
        "rendering across different Markdown processors."
    )

    example_valid = """\
# Document with Proper URLs

Visit <https://www.example.com/> for more information.

Contact us at <user@example.com> for support.

You can also use [example](https://www.example.com/) link syntax.

Not a clickable link: `https://www.example.com`

Reference: [https://example.com]

[example.com]: https://example.com
"""

    example_invalid = """\
# Document with Bare URLs

Visit https://www.example.com/ for more information.

Contact us at user@example.com for support.
"""

    # URLs (http, https, ftp) that have a host, with balanced parentheses support
    URL_PATTERN = re.compile(
        r"(?:https?|ftp)://"
        r"(?=[^\W_])"
        r"[^\s<>\[\]()\"'`]+"
        r"(?:\([^\s<>\[\]()\"'`]*\)[^\s<>\[\]()\"'`]*)*",
        re.IGNORECASE,
    )

    # Email addresses with an optional mailto: scheme. An address right after "/" is
    # the user part of a URL such as ssh://git@github.com/, so it is not matched.
    EMAIL_PATTERN = re.compile(
        r"(?<![a-zA-Z0-9._%+/-])(?:mailto:)?[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        re.IGNORECASE,
    )

    # Pattern to match HTML tags (used to exclude URLs in attributes)
    HTML_TAG_PATTERN = re.compile(r"<[a-zA-Z/][^>\n]*>")
    ANCHOR_OPEN_PATTERN = re.compile(r"<a[\s>]", re.IGNORECASE)
    ANCHOR_CLOSE_PATTERN = re.compile(r"</a\s*>", re.IGNORECASE)

    # Hugo shortcodes, whose quoted arguments break if a URL in them gets angle brackets
    SHORTCODE_PATTERN = re.compile(r"\{\{<.*?>\}\}|\{\{%.*?%\}\}", re.DOTALL)

    # GFM does not count these as part of a URL's end, e.g. a sentence's period or "**"
    TRAILING_PUNCT = ".,:;?!*_~"

    @classmethod
    def find_urls(cls, text: str) -> list[tuple[int, int]]:
        """Return (start, end) offsets of URLs and email addresses in text, in order.

        Context is ignored so that MD044 can use this to keep proper-name fixes out of
        URLs wherever they appear. An address inside a URL (``https://user@host/``)
        belongs to the URL, because two overlapping matches make the fix duplicate text.
        """
        urls = [
            (match.start(), match.start() + len(match.group().rstrip(cls.TRAILING_PUNCT)))
            for match in cls.URL_PATTERN.finditer(text)
        ]
        emails = [
            (match.start(), match.end())
            for match in cls.EMAIL_PATTERN.finditer(text)
            if not cls._overlaps_ranges(match.start(), match.end(), urls)
        ]
        return sorted(urls + emails)

    def _find_bare_urls(self, document: Document) -> Iterator[tuple[int, int, int, str]]:
        """Yield bare URL/email matches.

        Only inline content is scanned: front matter, code, HTML blocks and reference
        definitions are not rendered as Markdown text, so angle brackets added there
        would show up literally or change a value. Each block's lines are joined so
        that link text and ``<a>`` elements wrapping across lines are recognized.

        Yields tuples of (line_num, start, end, bare_text) where start/end are
        0-indexed column positions within the line.
        """
        blocks: dict[tuple[int, int], bool] = {}
        for token in document.tokens:
            if token.type != "inline" or not token.map or not token.children:
                continue
            # Table cells of one row share a map, so each row is scanned once.
            key = (token.map[0], token.map[1])
            has_links = any(child.type in ("link_open", "image") for child in token.children)
            blocks[key] = blocks.get(key, False) or has_links

        for (first, last), has_links in blocks.items():
            lines = document.lines[first:last]
            text = "\n".join(lines)
            line_starts = [0]
            for line in lines[:-1]:
                line_starts.append(line_starts[-1] + len(line) + 1)
            code = {
                line_starts[index] + column - 1
                for index in range(len(lines))
                for column in document.code_span_positions.get(first + index + 1, ())
            }
            excluded = self._excluded_ranges(text, code, has_links)

            for start, end in self.find_urls(text):
                if start > 0 and text[start - 1] in "<[(":
                    continue
                if start in code or self._overlaps_ranges(start, end, excluded):
                    continue
                index = bisect.bisect_right(line_starts, start) - 1
                column = start - line_starts[index]
                yield first + index + 1, column, column + end - start, text[start:end]

    def _excluded_ranges(self, text: str, code: set[int], has_links: bool) -> list[tuple[int, int]]:
        """Return offset ranges of a block whose URLs must not be wrapped.

        URLs in tag attributes and Hugo shortcodes are quoted arguments. URLs in link
        text or inside an ``<a>`` element are already linked, and wrapping them would
        nest a link inside a link.
        """
        ranges = [(match.start(), match.end()) for match in self.SHORTCODE_PATTERN.finditer(text)]
        for match in self.HTML_TAG_PATTERN.finditer(text):
            if match.start() in code:
                continue
            end = match.end()
            if self.ANCHOR_OPEN_PATTERN.match(match.group()):
                close = self.ANCHOR_CLOSE_PATTERN.search(text, end)
                if close:
                    end = close.end()
            ranges.append((match.start(), end))
        if has_links:
            ranges.extend(self._link_ranges(text, code))
        return ranges

    @classmethod
    def _link_ranges(cls, text: str, code: set[int]) -> list[tuple[int, int]]:
        """Return ranges of inline and full reference links, from "[" to the closing ")" or "]"."""
        ranges: list[tuple[int, int]] = []
        openers: list[int] = []
        index = 0
        while index < len(text):
            char = text[index]
            if index in code:
                pass
            elif char == "\\":
                index += 1
            elif char == "[":
                openers.append(index)
            elif char == "]" and openers:
                opener = openers.pop()
                end = cls._target_end(text, index + 1)
                if end is not None:
                    ranges.append((opener, end + 1))
                    index = end
            index += 1
        return ranges

    @staticmethod
    def _target_end(text: str, start: int) -> int | None:
        """Return the index closing a link destination "(...)" or label "[...]" at start."""
        if start >= len(text) or text[start] not in "([":
            return None
        opener = text[start]
        closer = ")" if opener == "(" else "]"
        depth = 0
        index = start
        while index < len(text):
            char = text[index]
            if char == "\\":
                index += 1
            elif char == opener:
                depth += 1
            elif char == closer:
                depth -= 1
                if depth == 0:
                    return index
            index += 1
        return None

    def check(self, document: Document, config: MD034Config) -> list[Violation]:
        """Check for bare URLs in the document."""
        return [
            Violation(
                line=line_num,
                column=start + 1,
                rule_id=self.id,
                rule_name=self.name,
                message=f"Bare URL used: {bare_text}",
                context=document.get_line(line_num),
            )
            for line_num, start, _, bare_text in self._find_bare_urls(document)
        ]

    def fix(self, document: Document, config: MD034Config) -> str | None:
        """Fix bare URLs and emails by wrapping them in angle brackets."""
        matches_by_line: dict[int, list[tuple[int, int, str]]] = {}
        for line_num, start, end, bare_text in self._find_bare_urls(document):
            matches_by_line.setdefault(line_num, []).append((start, end, bare_text))

        if not matches_by_line:
            return None

        lines = document.content.split("\n")
        for line_num, replacements in matches_by_line.items():
            line = lines[line_num - 1]
            for start, end, bare_text in sorted(replacements, key=lambda r: r[0], reverse=True):
                line = line[:start] + f"<{bare_text}>" + line[end:]
            lines[line_num - 1] = line

        return "\n".join(lines)
