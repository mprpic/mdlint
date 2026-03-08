from pathlib import Path

from mdlint.document import Document
from mdlint.linter import FileResult, Linter, LintResult
from mdlint.rules.base import Rule, RuleConfig
from mdlint.violation import Violation


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
        from mdlint.rules.md001 import MD001  # noqa: PLC0415

        rule = MD001()

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
        content = "# H1\n\n### H3\n"

        result = linter.fix_file(Path("test.md"), content=content)

        assert result.was_fixed is False
        md001_violations = [v for v in result.violations if v.rule_id == "MD001"]
        assert len(md001_violations) >= 1

    def test_fix_file_writes_back(self, tmp_path) -> None:
        """fix_file writes fixed content back to disk."""
        linter = Linter()
        test_file = tmp_path / "test.md"
        test_file.write_text("# Heading\n\nSome content.\n")

        result = linter.fix_file(test_file)

        # No fixable rules, so file should be unchanged
        assert result.was_fixed is False
        assert test_file.read_text() == "# Heading\n\nSome content.\n"

    def test_fix_stdin(self) -> None:
        """fix_stdin returns result and fixed content."""
        linter = Linter()
        content = "# Heading\n\nSome content.\n"

        result, fixed_content = linter.fix_stdin(content)

        assert result.path == Path("<stdin>")
        assert fixed_content == content
        assert result.was_fixed is False
