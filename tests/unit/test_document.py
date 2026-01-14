from pathlib import Path

from mdlint.document import Document
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
