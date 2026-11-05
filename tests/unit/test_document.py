from pathlib import Path

import pytest

from mdlint.document import Document, is_blank_line
from tests.conftest import load_fixture


class TestDocument:
    def test_simple_document_parsing(self) -> None:
        """Parse a simple markdown document."""
        content = load_fixture("document", "simple.md")
        doc = Document(Path("simple.md"), content)

        assert doc.path == Path("simple.md")
        assert doc.content == content
        assert len(doc.lines) > 0
        assert len(doc.tokens) > 0
        assert doc.front_matter is None

    def test_document_with_front_matter(self) -> None:
        """Parse document with YAML front matter."""
        content = load_fixture("document", "with_front_matter.md")
        doc = Document(Path("with_front_matter.md"), content)

        assert doc.front_matter is not None
        assert "title: Test Document" in doc.front_matter

    def test_empty_document(self) -> None:
        """Parse empty document."""
        content = load_fixture("document", "empty.md")
        doc = Document(Path("empty.md"), content)

        assert doc.content == ""
        assert len(doc.lines) == 0
        assert doc.front_matter is None

    def test_get_line(self) -> None:
        """Test get_line method."""
        content = load_fixture("document", "simple.md")
        doc = Document(Path("simple.md"), content)

        assert doc.get_line(1) == "# Simple Document"
        assert doc.get_line(0) is None
        assert doc.get_line(1000) is None

    def test_lines_split(self) -> None:
        """Test lines are split correctly."""
        content = load_fixture("document", "simple.md")
        doc = Document(Path("simple.md"), content)

        assert doc.lines[0] == "# Simple Document"


class TestFrontMatterLines:
    def test_lines_include_delimiters(self) -> None:
        content = load_fixture("document", "with_front_matter.md")
        doc = Document(Path("with_front_matter.md"), content)

        assert doc.front_matter_lines == {1, 2, 3, 4}

    def test_no_front_matter(self) -> None:
        content = load_fixture("document", "simple.md")
        doc = Document(Path("simple.md"), content)

        assert doc.front_matter_lines == set()


class TestIsBlankLine:
    @pytest.mark.parametrize(
        "line",
        [
            "",
            "   ",
            ">",
            "> >",
            ">  ",
            "<!-- x -->",
            "> <!-- prettier-ignore -->",
            "<!-- a --> <!-- b -->",
            "\t",
        ],
    )
    def test_blank(self, line: str) -> None:
        assert is_blank_line(line)

    @pytest.mark.parametrize(
        "line",
        ["text", "> text", "<!-- unclosed", "<!-- a --> x", "x <!-- a -->", "--> stray"],
    )
    def test_not_blank(self, line: str) -> None:
        assert not is_blank_line(line)


class TestContainerPrefix:
    # (line, container_prefix, continuation_prefix, blank_container_line)
    CASES = [
        (1, "", "", ""),  # front matter delimiter
        (2, "", "", ""),  # front matter body
        (5, "", "", ""),  # plain paragraph
        (7, "> ", "> ", ">"),
        (9, ">", ">", ">"),
        (11, "> > ", "> > ", "> >"),
        (13, "> - ", ">   ", ">"),
        (14, ">   ", ">   ", ">"),
        (16, "", "", ""),  # heading
        (18, "- ", "  ", ""),
        (19, "  ", "  ", ""),
        (23, "1. ", "   ", ""),
        (24, "   ", "   ", ""),
        (28, "-   ", "    ", ""),
        (29, "    ", "    ", ""),
        (33, "10) ", "    ", ""),
        (34, "    ", "    ", ""),
        (38, "- ", "  ", ""),
        (39, "  - ", "    ", ""),
        (40, "    ", "    ", ""),
        (44, "- ", "  ", ""),
        (45, "", "  ", ""),  # blank line inside the list item
        (46, "  > ", "  > ", "  >"),  # quote inside a list item
        (50, "> ", "> ", ">"),
        (51, "", "> ", ">"),  # lazy continuation
        (55, "> ", "> ", ">"),  # fence inside a quote
        (56, "> ", "> ", ">"),
        (57, "> ", "> ", ">"),
        (61, "- ", "  ", ""),
        (63, "  ", "  ", ""),  # table inside a list item
        (64, "  ", "  ", ""),
        (65, "  ", "  ", ""),
    ]

    @pytest.fixture
    def doc(self) -> Document:
        return Document(Path("containers.md"), load_fixture("document", "containers.md"))

    @pytest.mark.parametrize(("line", "prefix", "continuation", "blank"), CASES)
    def test_prefixes(
        self, doc: Document, line: int, prefix: str, continuation: str, blank: str
    ) -> None:
        assert doc.container_prefix(line) == prefix
        assert doc.continuation_prefix(line) == continuation
        assert doc.blank_container_line(line) == blank

    def test_prefix_is_leading_substring(self, doc: Document) -> None:
        for line_num, line in enumerate(doc.lines, start=1):
            assert line.startswith(doc.container_prefix(line_num))

    def test_out_of_range(self, doc: Document) -> None:
        assert doc.container_prefix(0) == ""
        assert doc.continuation_prefix(1000) == ""
        assert doc.blank_container_line(-1) == ""


class TestCodeSpanPositions:
    @pytest.fixture
    def doc(self) -> Document:
        return Document(Path("code_spans.md"), load_fixture("document", "code_spans.md"))

    @staticmethod
    def _cols(line: str, start: str, end: str, occurrence: int = 0) -> set[int]:
        """1-indexed columns from the start of `start` to the end of `end`."""
        begin = -1
        for _ in range(occurrence + 1):
            begin = line.index(start, begin + 1)
        finish = line.index(end, begin + len(start) - len(end)) + len(end)
        return set(range(begin + 1, finish + 1))

    def test_padded_double_and_wrapped_spans(self, doc: Document) -> None:
        line3 = doc.lines[2]
        expected3 = (
            self._cols(line3, "` a `", "` a `")
            | self._cols(line3, "`` `x` ``", "`` `x` ``")
            | set(range(line3.index("`wrapped") + 1, len(line3) + 1))
        )
        assert doc.code_span_positions[3] == expected3
        assert doc.code_span_positions[4] == {1, 2, 3, 4, 5}

    def test_simple_spans(self, doc: Document) -> None:
        line6 = doc.lines[5]
        assert doc.code_span_positions[6] == self._cols(line6, "`code`", "`code`") | self._cols(
            line6, "`more`", "`more`"
        )

    def test_table_cells(self, doc: Document) -> None:
        assert doc.code_span_positions[8] == self._cols(doc.lines[7], "`b`", "`b`")
        assert doc.code_span_positions[10] == self._cols(doc.lines[9], "`c`", "`c`")
        assert 9 not in doc.code_span_positions

    def test_span_wrapping_inside_blockquote(self, doc: Document) -> None:
        line12 = doc.lines[11]
        assert doc.code_span_positions[12] == set(
            range(line12.index("`multi") + 1, len(line12) + 1)
        )
        # The "> " container prefix of the continuation line is not part of the span.
        assert doc.code_span_positions[13] == {3, 4, 5, 6, 7}

    def test_escaped_and_unmatched_backticks(self, doc: Document) -> None:
        assert 15 not in doc.code_span_positions
        assert 17 not in doc.code_span_positions

    def test_stray_backtick_in_table_cell(self, doc: Document) -> None:
        """A backtick in one cell does not pair with a code span in another cell."""
        assert doc.code_span_positions[19] == self._cols(doc.lines[18], "`z`", "`z`")
        line21 = doc.lines[20]
        expected21 = self._cols(line21, "`p`", "`p`") | self._cols(line21, "`r`", "`r`")
        assert doc.code_span_positions[21] == expected21

    def test_backtick_inside_html_tag(self, doc: Document) -> None:
        """A backtick in a tag's attribute does not pair with the code spans after it."""
        line23 = doc.lines[22]
        expected23 = self._cols(line23, "`<b>`", "`<b>`") | self._cols(line23, "`<i>`", "`<i>`")
        assert doc.code_span_positions[23] == expected23
