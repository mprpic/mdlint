import bisect
import re
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import NamedTuple

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.front_matter import front_matter_plugin

_BLANK_LINE_PATTERN = re.compile(r"(?:\s|>|<!--(?:(?!-->).)*-->)*")
_BLOCKQUOTE_MARKER = re.compile(r" {0,3}>[ \t]?")
_LIST_MARKER = re.compile(r" {0,3}(?:[-+*]|\d{1,9}[.)])")


def is_blank_line(line: str) -> bool:
    """Whether a line separates blocks the way an empty line does.

    A line holding only blockquote markers is the blank line of a quote, and HTML comments
    render as nothing, so rules that require blank lines around blocks must accept both.
    Otherwise a directive such as ``<!-- prettier-ignore -->`` above a table would itself
    need a blank line, which detaches it from the block it targets.
    """
    return _BLANK_LINE_PATTERN.fullmatch(line) is not None


@dataclass
class _Container:
    """A blockquote or list item, as needed to peel its prefix off each line it spans."""

    kind: str  # "blockquote" or "list_item"
    start: int  # 0-indexed line of the opening marker
    width: int = 0  # list items: columns from the item's start to its content column


def _next_column(column: int, char: str) -> int:
    return column + 4 - column % 4 if char == "\t" else column + 1


def _list_item_start(line: str, pos: int, column: int) -> tuple[int, int] | None:
    """Return (prefix end index, content width) for a list marker line, per CommonMark."""
    match = _LIST_MARKER.match(line, pos)
    if not match:
        return None
    marker_end = match.end()
    marker_column = column + (marker_end - pos)
    end, space_column = marker_end, marker_column
    while end < len(line) and line[end] in " \t":
        space_column = _next_column(space_column, line[end])
        end += 1
    if end == len(line) or space_column - marker_column >= 5:
        # Blank first line or indented code: content starts one column after the marker.
        return min(marker_end + 1, len(line)), marker_column + 1 - column
    return end, space_column - column


def _peel_containers(line: str, index: int, chain: list[_Container]) -> tuple[str, str]:
    """Split a line's container prefix off, outermost container first.

    Returns the prefix actually present on the line and the prefix a new line inserted
    after it needs. Lazy continuation lines lack some markers, so peeling stops at the
    first container that is not present and the rest is synthesized for the second value.
    """
    pos = 0
    column = 0
    lazy = False
    continuation: list[str] = []
    for container in chain:
        if container.kind == "blockquote":
            match = None if lazy else _BLOCKQUOTE_MARKER.match(line, pos)
            if match is None:
                lazy = True
                continuation.append("> ")
                continue
            marker = match.group()
            # A bare ">" line still needs the marker's space before any new content.
            at_end = match.end() == len(line)
            continuation.append(marker + " " if at_end and marker[-1] == ">" else marker)
            for char in marker:
                column = _next_column(column, char)
            pos = match.end()
            continue

        if not lazy and index == container.start:
            start = _list_item_start(line, pos, column)
            if start is None:
                lazy = True
            else:
                pos, container.width = start
                column += container.width
        elif not lazy:
            end, reached, target = pos, column, column + container.width
            while end < len(line) and line[end] in " \t" and reached < target:
                after = _next_column(reached, line[end])
                if after > target:
                    break  # a tab straddling the content column cannot be split
                reached = after
                end += 1
            if reached < target and end < len(line) and line[end] not in " \t":
                lazy = True  # paragraph continuation without the item's indentation
            else:
                pos, column = end, reached
        continuation.append(" " * container.width)
    return line[:pos], "".join(continuation)


# An attribute of an HTML tag, as CommonMark defines it
_HTML_ATTRIBUTE = (
    r"(?:\s+[a-zA-Z_:][a-zA-Z0-9:._-]*"
    r"""(?:\s*=\s*(?:[^"'=<>`\x00-\x20]+|'[^']*'|"[^"]*"))?)"""
)

# CommonMark's raw HTML, which markdown-it parses as inline HTML: open and closing tags,
# comments, processing instructions, declarations and CDATA. Their whitespace includes line
# breaks, so a tag can wrap onto the next line.
RAW_HTML_PATTERN = re.compile(
    r"<[A-Za-z][A-Za-z0-9-]*" + _HTML_ATTRIBUTE + r"*\s*/?>"
    r"|</[A-Za-z][A-Za-z0-9-]*\s*>"
    r"|<!---?>|<!--(?:[^-]|-[^-]|--[^>])*-->"
    r"|<\?[\s\S]*?\?>"
    r"|<![A-Za-z][^>]*>"
    r"|<!\[CDATA\[[\s\S]*?\]\]>"
)

# URL and email autolinks
_AUTOLINK_PATTERN = re.compile(
    r"<[A-Za-z][A-Za-z0-9.+-]{1,31}:[^<>\x00-\x20]*>"
    r"|<[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*>"
)


def _find_code_spans(text: str) -> list[tuple[int, int]]:
    """Return (start, end) offsets of CommonMark code spans, delimiters included.

    Raw HTML and autolinks bind as tightly as code spans, so whichever starts first wins: a
    backtick inside a tag's attribute does not open a code span.
    """
    spans: list[tuple[int, int]] = []
    i = 0
    while i < len(text):
        char = text[i]
        if char == "\\":
            i += 2
            continue
        if char == "<" and (
            match := RAW_HTML_PATTERN.match(text, i) or _AUTOLINK_PATTERN.match(text, i)
        ):
            i = match.end()
            continue
        if char != "`":
            i += 1
            continue
        run_end = i
        while run_end < len(text) and text[run_end] == "`":
            run_end += 1
        run = run_end - i
        close = -1
        search = run_end
        while (found := text.find("`" * run, search)) >= 0:
            found_end = found
            while found_end < len(text) and text[found_end] == "`":
                found_end += 1
            if found_end - found == run:
                close = found
                break
            search = found_end
        if close < 0:
            i = run_end  # no matching closer: the run is literal text
            continue
        spans.append((i, close + run))
        i = close + run
    return spans


def _match_code_spans(
    text: str, spans: list[tuple[int, int]], contents: list[str]
) -> list[tuple[int, int]]:
    """Pair each parsed code span content, in order, with the scanned span that shows it."""
    matched: list[tuple[int, int]] = []
    next_span = 0
    for content in contents:
        wanted = _normalize_space(content)
        for k in range(next_span, len(spans)):
            span_start, span_end = spans[k]
            run = 0
            while text[span_start + run] == "`":
                run += 1
            if _normalize_space(text[span_start + run : span_end - run]) != wanted:
                continue
            next_span = k + 1
            matched.append(spans[k])
            break
    return matched


def _table_cell_ranges(row: str) -> list[tuple[int, int]]:
    """Return (start, end) offsets of a table row's cells, split as markdown-it splits them.

    Cells end at pipes not preceded by a backslash; the pipes at either end of the row do
    not start a cell.
    """
    start = len(row) - len(row.lstrip())
    end = len(row.rstrip())
    ranges: list[tuple[int, int]] = []
    cell_start = start
    escaped = False
    for pos in range(start, end):
        char = row[pos]
        if char == "|" and not escaped:
            ranges.append((cell_start, pos))
            cell_start = pos + 1
        escaped = char == "\\"
    ranges.append((cell_start, end))
    if ranges[0][0] == ranges[0][1]:
        ranges.pop(0)
    if ranges and ranges[-1][0] == ranges[-1][1]:
        ranges.pop()
    return ranges


def _normalize_space(text: str) -> str:
    return " ".join(text.split())


def normalize_reference_label(label: str) -> str:
    """Normalize a link label so that labels CommonMark treats as equal compare equal.

    Matching is case-insensitive with internal whitespace collapsed, so ``[Foo  Bar]:``
    defines the label that ``[text][foo bar]`` uses.
    """
    return _normalize_space(label).casefold()


class ReferenceDefinition(NamedTuple):
    """A link reference definition the parser recognized.

    The span covers every line the definition occupies, because the destination and title
    may wrap onto following lines and a fix that removes only the first line leaves the rest
    behind as stray text.
    """

    label: str  # normalized with normalize_reference_label()
    destination: str
    start_line: int  # 1-indexed, inclusive
    end_line: int  # 1-indexed, inclusive


class Document:
    """A parsed Markdown file.

    Attributes:
        path: File path (or Path("<stdin>") for stdin input).
        content: Raw file content.
        tokens: Parsed markdown-it-py tokens.
        lines: Content split by lines for source analysis.
        front_matter: Extracted front matter content if present.
    """

    _parser: MarkdownIt | None = None

    @classmethod
    def _get_parser(cls) -> MarkdownIt:
        if cls._parser is None:
            cls._parser = MarkdownIt().enable("table").use(front_matter_plugin)
        return cls._parser

    @classmethod
    def render_html(cls, content: str) -> str:
        """Render Markdown as HTML with the parser documents use.

        Fixes compare the rendering before and after an edit to make sure it keeps what a
        reader sees.
        """
        return cls._get_parser().render(content)

    def __init__(self, path: Path, content: str) -> None:
        """Initialize document with path and content.

        Args:
            path: File path or Path("<stdin>") for stdin.
            content: Raw Markdown content.
        """
        self.path = path
        self.content = content
        self.lines = content.splitlines()

        # markdown-it records the reference definitions it recognizes here, not in the tokens.
        self._parse_env: dict = {}
        self.tokens: list[Token] = self._get_parser().parse(content, self._parse_env)

        # Extract front matter if present
        self.front_matter: str | None = None
        for token in self.tokens:
            if token.type == "front_matter":
                self.front_matter = token.content
                break

    def get_line(self, line_number: int) -> str | None:
        """Get line content by 1-indexed line number.

        Args:
            line_number: 1-indexed line number.

        Returns:
            Line content or None if out of range.
        """
        if 1 <= line_number <= len(self.lines):
            return self.lines[line_number - 1]
        return None

    @cached_property
    def code_block_lines(self) -> set[int]:
        """1-indexed line numbers inside fenced/indented code blocks."""
        code_lines: set[int] = set()
        for token in self.tokens:
            if token.type in ("fence", "code_block") and token.map:
                for line_num in range(token.map[0] + 1, token.map[1] + 1):
                    code_lines.add(line_num)
        return code_lines

    @cached_property
    def html_block_lines(self) -> set[int]:
        """1-indexed line numbers inside HTML blocks."""
        html_lines: set[int] = set()
        for token in self.tokens:
            if token.type == "html_block" and token.map:
                for line_num in range(token.map[0] + 1, token.map[1] + 1):
                    html_lines.add(line_num)
        return html_lines

    @cached_property
    def front_matter_lines(self) -> frozenset[int]:
        """1-indexed line numbers of the front matter block, delimiters included.

        Frozen so a rule cannot add to it and change what later rules see.
        """
        for token in self.tokens:
            if token.type == "front_matter" and token.map:
                return frozenset(range(token.map[0] + 1, token.map[1] + 1))
        return frozenset()

    @cached_property
    def _container_prefixes(self) -> list[tuple[str, str]]:
        """Per 0-indexed line: (prefix present on the line, prefix for an inserted line)."""
        chains: list[list[_Container]] = [[] for _ in self.lines]
        for token in self.tokens:
            if token.type not in ("blockquote_open", "list_item_open") or not token.map:
                continue
            kind = "blockquote" if token.type == "blockquote_open" else "list_item"
            container = _Container(kind=kind, start=token.map[0])
            for index in range(token.map[0], min(token.map[1], len(self.lines))):
                chains[index].append(container)
        return [
            _peel_containers(line, index, chain)
            for index, (line, chain) in enumerate(zip(self.lines, chains, strict=True))
        ]

    def container_prefix(self, line_number: int) -> str:
        """Leading text of a line that belongs to enclosing blockquotes and list items.

        Rules that inspect or rewrite a line's own content must skip this prefix and put it
        back, otherwise ``> `` markers and list indentation get measured as content or lost.
        Lazy continuation lines only carry the markers actually present.
        """
        if 1 <= line_number <= len(self.lines):
            return self._container_prefixes[line_number - 1][0]
        return ""

    def continuation_prefix(self, line_number: int) -> str:
        """Prefix a new non-blank line inserted after this line needs to stay in its containers.

        List markers become spaces of the same width, and blockquote markers missing from a
        lazy line are restored.
        """
        if 1 <= line_number <= len(self.lines):
            return self._container_prefixes[line_number - 1][1]
        return ""

    def blank_container_line(self, line_number: int) -> str:
        """Text to insert as a blank line after this line without leaving its containers.

        A bare empty line would end an enclosing blockquote, so inside quotes this is the
        quote marker (for example ``>``), and an empty string elsewhere.
        """
        return self.continuation_prefix(line_number).rstrip()

    def blank_line_between(self, above: int, below: int) -> str:
        """Blank line to insert between two 1-indexed lines without splitting a blockquote.

        An empty line would end a quote that both lines are in, so inside one this is the
        ``>`` marker. The shallower side wins, so a blank line next to a quote that starts or
        ends there is not itself quoted.
        """
        candidates = (self.blank_container_line(above), self.blank_container_line(below))
        return min(candidates, key=lambda text: text.count(">"))

    def follows_bare_list_marker(self, start: int) -> bool:
        """Whether a block starting at 0-indexed line `start` opens a bare list item.

        A list item can begin with at most one blank line, so after a marker that sits alone
        on its line a blank line would end the item and push the block out of the list.
        """
        marker_line = self.get_line(start)
        if marker_line is None or marker_line[len(self.container_prefix(start)) :].strip():
            return False
        return self._list_item_ends.get(start - 1, 0) > start

    @cached_property
    def _list_item_ends(self) -> dict[int, int]:
        """Furthest end line of the list items opening on each 0-indexed line.

        Rules ask about every heading, fence and table, so this is built once instead of
        scanning all tokens per question.
        """
        ends: dict[int, int] = {}
        for token in self.tokens:
            if token.type == "list_item_open" and token.map is not None:
                ends[token.map[0]] = max(ends.get(token.map[0], 0), token.map[1])
        return ends

    @cached_property
    def code_span_positions(self) -> dict[int, set[int]]:
        """Column positions inside inline code spans.

        Spans are found by scanning the raw source, because markdown-it's ``code_inline``
        content drops padding spaces and line breaks and so cannot be searched for. Each
        scanned span is kept only if it lines up with a parsed ``code_inline`` token, which
        filters out backticks that the parser treated as something else.

        Returns:
            Dict mapping 1-indexed line numbers to sets of 1-indexed column
            positions that are inside inline code spans.
        """
        expected: dict[tuple[int, int], list[str]] = {}
        table_rows: dict[int, list[list[str]]] = {}
        for index, token in enumerate(self.tokens):
            if token.type != "inline" or not token.map or token.children is None:
                continue
            contents = [child.content for child in token.children if child.type == "code_inline"]
            if index > 0 and self.tokens[index - 1].type in ("th_open", "td_open"):
                # The cells of a row share its map; they are scanned one by one so that a
                # stray backtick in one cell cannot pair with a code span in another.
                table_rows.setdefault(token.map[0], []).append(contents)
            elif contents:
                expected.setdefault((token.map[0], token.map[1]), []).extend(contents)

        code_columns: dict[int, set[int]] = {}
        for (start, end), contents in expected.items():
            self._mark_code_spans(start, end, contents, code_columns)
        for row, cells in table_rows.items():
            self._mark_table_code_spans(row, cells, code_columns)
        return code_columns

    def _mark_code_spans(
        self, start: int, end: int, contents: list[str], code_columns: dict[int, set[int]]
    ) -> None:
        """Record the columns of the code spans in one inline block's lines.

        Container prefixes are removed before scanning so a span wrapping inside a quote
        compares equal to the parsed content, and the prefix columns are not marked.
        """
        line_numbers: list[int] = []
        line_skips: list[int] = []
        offsets: list[int] = []
        parts: list[str] = []
        offset = 0
        for line_number in range(start + 1, end + 1):
            line = self.get_line(line_number)
            if line is None or line_number in self.code_block_lines:
                continue
            skip = len(self.container_prefix(line_number))
            line_numbers.append(line_number)
            line_skips.append(skip)
            offsets.append(offset)
            parts.append(line[skip:])
            offset += len(line) - skip + 1
        text = "\n".join(parts)

        for span_start, span_end in _match_code_spans(text, _find_code_spans(text), contents):
            for position in range(span_start, span_end):
                if text[position] == "\n":
                    continue
                part = bisect.bisect_right(offsets, position) - 1
                column = line_skips[part] + position - offsets[part] + 1
                code_columns.setdefault(line_numbers[part], set()).add(column)

    def _mark_table_code_spans(
        self, row: int, cells: list[list[str]], code_columns: dict[int, set[int]]
    ) -> None:
        """Record the columns of the code spans in the table row on 0-indexed line `row`."""
        line_number = row + 1
        line = self.get_line(line_number)
        if line is None:
            return
        skip = len(self.container_prefix(line_number))
        text = line[skip:]
        for (cell_start, cell_end), contents in zip(_table_cell_ranges(text), cells):
            cell = text[cell_start:cell_end]
            offset = skip + cell_start
            for span_start, span_end in _match_code_spans(cell, _find_code_spans(cell), contents):
                columns = range(offset + span_start + 1, offset + span_end + 1)
                code_columns.setdefault(line_number, set()).update(columns)

    # Pattern to match reference definitions: [ref]: destination [optional title]
    # It only approximates the syntax on a single line without container prefixes; use
    # reference_definition_lines to know whether a line really is a definition.
    REFERENCE_DEF_PATTERN = re.compile(
        r"^\s*\[([^\]]+)\]:\s*"
        r"([^\s\"'(]+|<[^>]*>)"  # destination (bare or angle-bracketed)
        r"(?:\s+[\"'(].*)?\s*$"  # optional title
    )

    @cached_property
    def reference_definition_entries(self) -> list[ReferenceDefinition]:
        """Every reference definition in source order, duplicate labels included.

        Taken from the parser rather than a line regex so that definitions inside code
        blocks or ending in prose are excluded, ones inside blockquotes and list items are
        included, and wrapped definitions keep all their lines.
        """
        first = [
            (label, ref["href"], ref["map"])
            for label, ref in self._parse_env.get("references", {}).items()
        ]
        duplicates = [
            (ref["label"], ref["href"], ref["map"])
            for ref in self._parse_env.get("duplicate_refs", [])
        ]
        definitions = [
            ReferenceDefinition(
                label=normalize_reference_label(label),
                destination=href,
                start_line=line_map[0] + 1,
                end_line=line_map[1],
            )
            for label, href, line_map in first + duplicates
        ]
        return sorted(definitions, key=lambda definition: definition.start_line)

    @cached_property
    def reference_definition_lines(self) -> frozenset[int]:
        """1-indexed line numbers occupied by reference definitions."""
        return frozenset(
            line
            for definition in self.reference_definition_entries
            for line in range(definition.start_line, definition.end_line + 1)
        )

    @cached_property
    def reference_definitions(self) -> dict[str, str]:
        """Reference definitions mapping normalized labels to destinations.

        Labels are normalized with normalize_reference_label(); the first definition of a
        label wins, as it does when the document is rendered.
        """
        definitions: dict[str, str] = {}
        for definition in self.reference_definition_entries:
            definitions.setdefault(definition.label, definition.destination)
        return definitions
