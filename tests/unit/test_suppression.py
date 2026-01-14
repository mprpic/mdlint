from pathlib import Path

from mdlint.document import Document
from mdlint.suppression import Directive, _is_suppressed, _parse_directives, filter_suppressed
from mdlint.violation import Violation


def _make_doc(content: str) -> Document:
    return Document(Path("test.md"), content)


def _make_violation(line: int, rule_id: str = "MD001") -> Violation:
    return Violation(
        line=line,
        column=1,
        rule_id=rule_id,
        rule_name="test-rule",
        message="Test violation",
    )


class TestParseDirectives:
    """Tests for _parse_directives."""

    def test_single_rule(self) -> None:
        doc = _make_doc("<!-- mdlint: disable MD001 -->\n")
        directives = _parse_directives(doc)

        assert len(directives) == 1
        assert directives[0].kind == "disable"
        assert directives[0].rule_ids == ["MD001"]
        assert directives[0].line == 1

    def test_multiple_rules(self) -> None:
        doc = _make_doc("<!-- mdlint: disable MD001 MD013 MD033 -->\n")
        directives = _parse_directives(doc)

        assert len(directives) == 1
        assert directives[0].rule_ids == ["MD001", "MD013", "MD033"]

    def test_blanket_disable(self) -> None:
        doc = _make_doc("<!-- mdlint: disable -->\n")
        directives = _parse_directives(doc)

        assert len(directives) == 1
        assert directives[0].kind == "disable"
        assert directives[0].rule_ids == []

    def test_enable(self) -> None:
        doc = _make_doc("<!-- mdlint: enable MD001 -->\n")
        directives = _parse_directives(doc)

        assert len(directives) == 1
        assert directives[0].kind == "enable"

    def test_disable_next_line(self) -> None:
        doc = _make_doc("<!-- mdlint: disable-next-line MD001 -->\n")
        directives = _parse_directives(doc)

        assert len(directives) == 1
        assert directives[0].kind == "disable-next-line"

    def test_multiple_directives(self) -> None:
        doc = _make_doc(
            "# Heading\n<!-- mdlint: disable MD001 -->\n### Skip\n<!-- mdlint: enable MD001 -->\n"
        )
        directives = _parse_directives(doc)

        assert len(directives) == 2
        assert directives[0].line == 2
        assert directives[1].line == 4

    def test_code_block_excluded(self) -> None:
        doc = _make_doc("# Heading\n\n```\n<!-- mdlint: disable MD001 -->\n```\n")
        directives = _parse_directives(doc)

        assert len(directives) == 0

    def test_malformed_comment_ignored(self) -> None:
        doc = _make_doc("<!-- mdlint: invalid MD001 -->\n")
        directives = _parse_directives(doc)

        assert len(directives) == 0

    def test_not_a_comment(self) -> None:
        doc = _make_doc("mdlint: disable MD001\n")
        directives = _parse_directives(doc)

        assert len(directives) == 0

    def test_indented_directive(self) -> None:
        doc = _make_doc("  <!-- mdlint: disable MD001 -->\n")
        directives = _parse_directives(doc)

        assert len(directives) == 1

    def test_extra_whitespace(self) -> None:
        doc = _make_doc("<!--  mdlint:  disable  MD001  -->\n")
        directives = _parse_directives(doc)

        assert len(directives) == 1
        assert directives[0].rule_ids == ["MD001"]


class TestIsSuppressed:
    """Tests for _is_suppressed."""

    def test_not_suppressed_without_directives(self) -> None:
        assert not _is_suppressed("MD001", 1, [])

    def test_suppressed_by_disable(self) -> None:
        directives = [Directive(line=1, kind="disable", rule_ids=["MD001"])]
        assert _is_suppressed("MD001", 2, directives)

    def test_not_suppressed_different_rule(self) -> None:
        directives = [Directive(line=1, kind="disable", rule_ids=["MD013"])]
        assert not _is_suppressed("MD001", 2, directives)

    def test_suppressed_by_blanket_disable(self) -> None:
        directives = [Directive(line=1, kind="disable", rule_ids=[])]
        assert _is_suppressed("MD001", 2, directives)
        assert _is_suppressed("MD013", 2, directives)

    def test_reenabled_after_enable(self) -> None:
        directives = [
            Directive(line=1, kind="disable", rule_ids=["MD001"]),
            Directive(line=3, kind="enable", rule_ids=["MD001"]),
        ]
        assert _is_suppressed("MD001", 2, directives)
        assert not _is_suppressed("MD001", 4, directives)

    def test_blanket_enable_resets_all(self) -> None:
        directives = [
            Directive(line=1, kind="disable", rule_ids=["MD001"]),
            Directive(line=2, kind="disable", rule_ids=["MD013"]),
            Directive(line=3, kind="enable", rule_ids=[]),
        ]
        assert not _is_suppressed("MD001", 4, directives)
        assert not _is_suppressed("MD013", 4, directives)

    def test_enable_within_blanket_disable(self) -> None:
        directives = [
            Directive(line=1, kind="disable", rule_ids=[]),
            Directive(line=2, kind="enable", rule_ids=["MD001"]),
        ]
        # MD001 is re-enabled, so not suppressed
        assert not _is_suppressed("MD001", 3, directives)
        # MD013 is still suppressed by blanket disable
        assert _is_suppressed("MD013", 3, directives)

    def test_disable_next_line(self) -> None:
        directives = [Directive(line=2, kind="disable-next-line", rule_ids=["MD001"])]
        assert not _is_suppressed("MD001", 2, directives)
        assert _is_suppressed("MD001", 3, directives)
        assert not _is_suppressed("MD001", 4, directives)

    def test_disable_next_line_blanket(self) -> None:
        directives = [Directive(line=2, kind="disable-next-line", rule_ids=[])]
        assert _is_suppressed("MD001", 3, directives)
        assert _is_suppressed("MD013", 3, directives)
        assert not _is_suppressed("MD001", 4, directives)

    def test_not_suppressed_before_directive(self) -> None:
        directives = [Directive(line=5, kind="disable", rule_ids=["MD001"])]
        assert not _is_suppressed("MD001", 3, directives)


class TestFilterSuppressed:
    """Tests for filter_suppressed."""

    def test_no_directives_passthrough(self) -> None:
        doc = _make_doc("# Heading\n\n### Skip\n")
        violations = [_make_violation(3)]

        result = filter_suppressed(doc, violations)

        assert result == violations

    def test_disable_range(self) -> None:
        doc = _make_doc(
            "# Heading\n"
            "<!-- mdlint: disable MD001 -->\n"
            "### Skip\n"
            "<!-- mdlint: enable MD001 -->\n"
            "##### After\n"
        )
        violations = [_make_violation(3), _make_violation(5)]

        result = filter_suppressed(doc, violations)

        assert len(result) == 1
        assert result[0].line == 5

    def test_disable_next_line(self) -> None:
        doc = _make_doc(
            "# Heading\n<!-- mdlint: disable-next-line MD001 -->\n### Skip\n##### After\n"
        )
        violations = [_make_violation(3), _make_violation(4)]

        result = filter_suppressed(doc, violations)

        assert len(result) == 1
        assert result[0].line == 4

    def test_md033_exemption(self) -> None:
        doc = _make_doc("# Heading\n<!-- mdlint: disable MD001 -->\n### Skip\n")
        violations = [
            _make_violation(2, "MD033"),
            _make_violation(3, "MD001"),
        ]

        result = filter_suppressed(doc, violations)

        assert len(result) == 0

    def test_md033_not_exempted_on_non_directive_lines(self) -> None:
        doc = _make_doc("# Heading\n<!-- mdlint: disable MD001 -->\n<!-- some other comment -->\n")
        violations = [_make_violation(3, "MD033")]

        result = filter_suppressed(doc, violations)

        assert len(result) == 1

    def test_blanket_disable(self) -> None:
        doc = _make_doc("# Heading\n<!-- mdlint: disable -->\n### Skip\n##### Also skip\n")
        violations = [_make_violation(3), _make_violation(4)]

        result = filter_suppressed(doc, violations)

        assert len(result) == 0

    def test_enable_within_blanket_disable(self) -> None:
        doc = _make_doc(
            "# Heading\n"
            "<!-- mdlint: disable -->\n"
            "<!-- mdlint: enable MD001 -->\n"
            "### Should trigger MD001\n"
        )
        violations = [
            _make_violation(4, "MD001"),
            _make_violation(4, "MD013"),
        ]

        result = filter_suppressed(doc, violations)

        assert len(result) == 1
        assert result[0].rule_id == "MD001"

    def test_empty_violations(self) -> None:
        doc = _make_doc("<!-- mdlint: disable -->\n# Heading\n")

        result = filter_suppressed(doc, [])

        assert result == []
