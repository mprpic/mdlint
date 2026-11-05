from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.linter import MAX_FIX_PASSES, FileResult, Linter, LintResult
from mdlint.rules import RULE_REGISTRY
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation
from tests.conftest import load_fixture


class TestRuleFixDefault:
    """Tests for the default Rule.fix() implementation."""

    def test_fix_returns_none(self) -> None:
        """Default fix() returns None (nothing to fix)."""
        # Use any concrete rule to test the default behavior
        from mdlint.rules.md001 import MD001, MD001Config  # noqa: PLC0415

        rule = MD001()
        document = Document(Path("test.md"), "# Heading\n")
        result = rule.fix(document, MD001Config())

        assert result is None

    def test_fixable_false_by_default(self) -> None:
        """Rules without fix() override are not fixable."""
        from mdlint.rules.md013 import MD013  # noqa: PLC0415

        rule = MD013()

        assert rule.fixable is False

    def test_fixable_true_when_overridden(self) -> None:
        """Rules with fix() override are fixable."""

        class FixableRule(Rule):
            id = "TEST"
            name = "test-fixable"
            summary = "Test fixable rule"

            def check(self, document: Document, config: RuleConfig) -> list[Violation]:
                return []

            def fix(self, document: Document, config: RuleConfig) -> str | None:
                return document.content.replace("bad", "good")

        rule = FixableRule()

        assert rule.fixable is True


class TestFileResultWasFixed:
    """Tests for FileResult.was_fixed field."""

    def test_default_was_fixed_is_false(self) -> None:
        """FileResult defaults to was_fixed=False."""
        result = FileResult(path=Path("test.md"))

        assert result.was_fixed is False

    def test_was_fixed_can_be_set(self) -> None:
        """FileResult.was_fixed can be set to True."""
        result = FileResult(path=Path("test.md"), was_fixed=True)

        assert result.was_fixed is True


class TestLintResultFilesFixed:
    """Tests for LintResult.files_fixed property."""

    def test_no_files_fixed(self) -> None:
        """files_fixed is 0 when no files were fixed."""
        result = LintResult(
            files=[
                FileResult(path=Path("a.md")),
                FileResult(path=Path("b.md")),
            ]
        )

        assert result.files_fixed == 0

    def test_some_files_fixed(self) -> None:
        """files_fixed counts files where was_fixed is True."""
        result = LintResult(
            files=[
                FileResult(path=Path("a.md"), was_fixed=True),
                FileResult(path=Path("b.md")),
                FileResult(path=Path("c.md"), was_fixed=True),
            ]
        )

        assert result.files_fixed == 2


class TestLinterFixFile:
    """Tests for Linter.fix_file() method."""

    def test_fix_file_no_fixable_rules(self) -> None:
        """fix_file with no fixable rules returns unfixed result."""
        linter = Linter()
        content = "# Heading\n\nSome content.\n"

        result = linter.fix_file(Path("test.md"), content=content)

        assert result.was_fixed is False
        assert result.content == content

    def test_fix_file_preserves_violations(self) -> None:
        """fix_file still reports remaining violations."""
        linter = Linter()
        content = "# Heading\n\n# Heading\n"

        result = linter.fix_file(Path("test.md"), content=content)

        assert result.was_fixed is False
        md024_violations = [v for v in result.violations if v.rule_id == "MD024"]
        assert len(md024_violations) >= 1

    def test_fix_file_with_line_separators_in_text(self, tmp_path) -> None:
        """Characters that str.splitlines() treats as line breaks do not shift fixes."""
        content = load_fixture("document", "line_separators.md")
        test_file = tmp_path / "test.md"
        test_file.write_text(content, encoding="utf-8")

        result = Linter().fix_file(test_file)

        expected = content.replace("separator   \n", "separator\n")
        assert result.content == expected
        assert test_file.read_text(encoding="utf-8") == expected

    def test_fix_file_writes_back(self, tmp_path) -> None:
        """fix_file writes fixed content back to disk."""
        linter = Linter()
        test_file = tmp_path / "test.md"
        test_file.write_text("# Heading\n\nSome content.\n")

        result = linter.fix_file(test_file)

        # No fixable rules, so file should be unchanged
        assert result.was_fixed is False
        assert test_file.read_text() == "# Heading\n\nSome content.\n"

    def test_fix_file_respects_suppression(self) -> None:
        """fix_file skips fixes for rules suppressed by inline directives."""
        linter = Linter(enabled_rules={"MD047"})
        content = load_fixture("suppression", "fix_suppressed.md")

        result = linter.fix_file(Path("test.md"), content=content)

        assert result.was_fixed is False
        assert result.content == content

    def test_fix_file_applies_non_suppressed(self, tmp_path) -> None:
        """fix_file still applies fixes for rules that are not suppressed."""
        linter = Linter(enabled_rules={"MD047"})
        content = load_fixture("md047", "invalid.md")
        test_file = tmp_path / "test.md"
        test_file.write_text(content)

        result = linter.fix_file(test_file, content=content)

        assert result.was_fixed is True
        assert result.content.endswith("\n")

    def test_fix_stdin(self) -> None:
        """fix_stdin returns result and fixed content."""
        linter = Linter()
        content = "# Heading\n\nSome content.\n"

        result, fixed_content = linter.fix_stdin(content)

        assert result.path == Path("<stdin>")
        assert fixed_content == content
        assert result.was_fixed is False


class TestFixPreservesEncoding:
    """Fixes keep the file's line endings and byte order mark."""

    def test_crlf_preserved_on_write(self, tmp_path) -> None:
        """CRLF files are written back with CRLF line endings."""
        content = load_fixture("linter", "trailing_spaces.md").replace("\n", "\r\n")
        test_file = tmp_path / "test.md"
        test_file.write_bytes(content.encode("utf-8"))

        result = Linter(enabled_rules={"MD009"}).fix_file(test_file)

        assert result.was_fixed is True
        assert test_file.read_bytes() == b"# Title\r\n\r\nTrailing\r\nText\r\n"

    def test_crlf_preserved_on_stdin(self) -> None:
        """Fixed stdin content keeps CRLF line endings."""
        content = load_fixture("linter", "trailing_spaces.md").replace("\n", "\r\n")

        result, fixed = Linter(enabled_rules={"MD009"}).fix_stdin(content)

        assert result.violations == []
        assert fixed == "# Title\r\n\r\nTrailing\r\nText\r\n"

    def test_bom_preserved_on_write(self, tmp_path) -> None:
        """A leading byte order mark is kept and not reported as content."""
        content = "\ufeff" + load_fixture("linter", "trailing_spaces.md")
        test_file = tmp_path / "test.md"
        test_file.write_bytes(content.encode("utf-8"))

        result = Linter().fix_file(test_file)

        assert result.was_fixed is True
        assert result.violations == []
        assert test_file.read_bytes() == "\ufeff# Title\n\nTrailing\nText\n".encode()

    def test_unchanged_file_not_rewritten(self, tmp_path) -> None:
        """A file with nothing to fix keeps its exact bytes."""
        content = "\ufeff" + load_fixture("linter", "clean.md").replace("\n", "\r\n")
        test_file = tmp_path / "test.md"
        test_file.write_bytes(content.encode("utf-8"))

        result = Linter().fix_file(test_file)

        assert result.was_fixed is False
        assert test_file.read_bytes() == content.encode("utf-8")

    def test_invalid_utf8_reported_as_error(self, tmp_path) -> None:
        """Undecodable files become a per-file error instead of an exception."""
        test_file = tmp_path / "bad.md"
        test_file.write_bytes(b"# Title\n\ncaf\xe9 trailing   \n")

        result = Linter().fix_file(test_file)

        assert result.error is not None
        assert "utf-8" in result.error
        assert test_file.read_bytes() == b"# Title\n\ncaf\xe9 trailing   \n"


class TestFixSuppression:
    """A rule with a suppressed violation is not fixed in that file, but still reported."""

    @pytest.mark.parametrize(
        ("rule_id", "fixture", "remaining"),
        [
            ("MD009", "fix_suppressed_range.md", [6]),
            ("MD022", "fix_suppressed_insertion.md", [1]),
            # Fixing the other fences would rewrite one fence of the suppressed block
            ("MD048", "fix_suppressed_fences.md", [12]),
            ("MD022", "fix_suppressed_heading_nearby.md", [5, 5]),
        ],
    )
    def test_rule_with_suppression_is_not_fixed(
        self, rule_id: str, fixture: str, remaining: list[int]
    ) -> None:
        linter = Linter(enabled_rules={rule_id})
        content = load_fixture("linter", fixture)

        result, fixed = linter.fix_stdin(content)

        assert fixed == content
        assert [v.line for v in result.violations] == remaining


def _char_violations(rule: Rule, document: Document, char: str) -> list[Violation]:
    return [
        Violation(line=1, column=i + 1, rule_id=rule.id, rule_name=rule.name, message=char)
        for i, c in enumerate(document.content)
        if c == char
    ]


class _ReplaceAWithB(Rule):
    id = "TEST1"
    name = "test-a-to-b"
    summary = "Flags 'a' and replaces it with 'b'"

    def check(self, document: Document, config: RuleConfig) -> list[Violation]:
        return _char_violations(self, document, "a")

    def fix(self, document: Document, config: RuleConfig) -> str | None:
        return document.content.replace("a", "b")


class _ReplaceCWithA(Rule):
    """Runs after TEST1, so every 'a' it creates needs another pass."""

    id = "TEST2"
    name = "test-c-to-a"
    summary = "Flags 'c' and replaces it with 'a'"

    def check(self, document: Document, config: RuleConfig) -> list[Violation]:
        return _char_violations(self, document, "c")

    def fix(self, document: Document, config: RuleConfig) -> str | None:
        return document.content.replace("c", "a")


class _AlwaysAppend(Rule):
    """Mimics a fix that never resolves its violation and grows the file."""

    id = "TEST3"
    name = "test-append"
    summary = "Always flags line 1 and appends a line"

    def check(self, document: Document, config: RuleConfig) -> list[Violation]:
        return [Violation(line=1, column=1, rule_id=self.id, rule_name=self.name, message="x")]

    def fix(self, document: Document, config: RuleConfig) -> str | None:
        return document.content + "more\n"


class _RemoveOneX(Rule):
    """Makes progress on every pass but needs one pass per 'x'."""

    id = "TEST4"
    name = "test-remove-x"
    summary = "Flags 'x' and removes one per fix"

    def check(self, document: Document, config: RuleConfig) -> list[Violation]:
        return _char_violations(self, document, "x")

    def fix(self, document: Document, config: RuleConfig) -> str | None:
        return document.content.replace("x", "", 1)


class TestFixConvergence:
    """Fixable rules run repeatedly until the content stops improving."""

    @pytest.fixture(autouse=True)
    def _fake_rules(self, monkeypatch) -> None:
        for rule_class in (_ReplaceAWithB, _ReplaceCWithA, _AlwaysAppend, _RemoveOneX):
            monkeypatch.setitem(RULE_REGISTRY, rule_class.id, rule_class)

    def test_fix_repeats_until_clean(self) -> None:
        """A violation created by a later rule is fixed in a second pass."""
        linter = Linter(enabled_rules={"TEST1", "TEST2"})

        result, fixed = linter.fix_stdin("a c\n")

        assert fixed == "b b\n"
        assert result.was_fixed is True
        assert result.violations == []

    def test_fix_stops_when_pass_makes_no_progress(self) -> None:
        """A pass that does not reduce the remaining violations is discarded."""
        linter = Linter(enabled_rules={"TEST3"})

        result, fixed = linter.fix_stdin("text\n")

        assert fixed == "text\nmore\n"
        assert len(result.violations) == 1

    def test_fix_stops_after_max_passes(self) -> None:
        """The number of passes is capped even while each one makes progress."""
        linter = Linter(enabled_rules={"TEST4"})

        result, fixed = linter.fix_stdin("x" * 15 + "\n")

        assert fixed == "x" * (15 - MAX_FIX_PASSES) + "\n"
        assert len(result.violations) == 15 - MAX_FIX_PASSES


class TestFixGrowthBounded:
    """Real fixes that grow the file on every run are applied once per run, not per pass."""

    @pytest.mark.parametrize(
        "filename", ["fix_grows_list_in_quote.md", "fix_grows_heading_in_quote.md"]
    )
    def test_growing_fix_is_bounded(self, filename: str) -> None:
        """Fixes that add a line on every run are not repeated within one run."""
        content = load_fixture("linter", filename)

        _, fixed = Linter().fix_stdin(content)

        assert fixed.count("\n") <= content.count("\n") + 1
