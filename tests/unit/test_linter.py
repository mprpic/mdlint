import os
from pathlib import Path

from mdlint.linter import FileResult, Linter, LintResult, discover_files
from mdlint.rules import RULE_REGISTRY
from mdlint.violation import Violation
from tests.conftest import fixture_path


class TestFileResult:
    """Tests for FileResult dataclass."""

    def test_empty_result(self) -> None:
        """FileResult with no violations."""
        result = FileResult(path=Path("test.md"))

        assert result.path == Path("test.md")
        assert len(result.violations) == 0
        assert result.error is None

    def test_result_with_error(self) -> None:
        """FileResult with error."""
        result = FileResult(path=Path("missing.md"), error="File not found")

        assert result.error == "File not found"
        assert len(result.violations) == 0


class TestLintResult:
    """Tests for LintResult dataclass."""

    def test_empty_result(self) -> None:
        """LintResult with no files."""
        result = LintResult()

        assert result.files_checked == 0
        assert result.total_violations == 0
        assert result.exit_code == 0

    def test_result_with_violations(self) -> None:
        """LintResult with violations."""
        violation = Violation(
            line=1,
            column=1,
            rule_id="MD001",
            rule_name="heading-increment",
            message="Test violation",
        )
        file_result = FileResult(path=Path("test.md"), violations=[violation])
        result = LintResult(files=[file_result])

        assert result.files_checked == 1
        assert result.files_with_violations == 1
        assert result.total_violations == 1
        assert result.exit_code == 1

    def test_result_with_errors_only(self) -> None:
        """LintResult with errors but no violations."""
        file_result = FileResult(path=Path("test.md"), error="Read error")
        result = LintResult(files=[file_result])

        assert result.files_with_errors == 1
        assert result.total_violations == 0
        assert result.exit_code == 2


class TestLinter:
    """Tests for Linter class."""

    def test_lint_clean_file(self) -> None:
        """Lint a file with no violations."""
        linter = Linter()
        path = fixture_path("linter", "clean.md")

        result = linter.lint_file(path)

        assert len(result.violations) == 0
        assert result.error is None

    def test_lint_file_with_violations(self) -> None:
        """Lint a file with violations."""
        linter = Linter()
        path = fixture_path("linter", "with_violations.md")

        result = linter.lint_file(path)

        assert len(result.violations) >= 1

    def test_lint_stdin(self) -> None:
        """Lint content from stdin."""
        linter = Linter()
        content = "# Valid heading\n\nSome content.\n"

        result = linter.lint_stdin(content)

        assert result.path == Path("<stdin>")

    def test_lint_with_disabled_rules(self) -> None:
        """Lint with some rules disabled via enabled_rules."""
        # Enable all rules except MD001
        enabled = set(RULE_REGISTRY.keys()) - {"MD001"}
        linter = Linter(enabled_rules=enabled)
        path = fixture_path("linter", "with_violations.md")

        result = linter.lint_file(path)

        # Should not have MD001 violations
        assert all(v.rule_id != "MD001" for v in result.violations)

    def test_lint_file_not_found(self) -> None:
        """Lint a file that doesn't exist returns error."""
        linter = Linter()
        path = Path("/nonexistent/path/to/file.md")

        result = linter.lint_file(path)

        assert result.error is not None
        assert len(result.violations) == 0

    def test_lint_empty_file(self) -> None:
        """Lint an empty file produces no violations."""
        linter = Linter()
        result = linter.lint_file(Path("empty.md"), content="")

        assert len(result.violations) == 0
        assert result.error is None

    def test_lint_front_matter_only(self) -> None:
        """Lint a file with only front matter."""
        linter = Linter()
        content = "---\ntitle: Test\nauthor: Test Author\n---\n"

        result = linter.lint_file(Path("frontmatter.md"), content=content)

        assert result.error is None

    def test_lint_paths_multiple_files(self, tmp_path: Path) -> None:
        """Lint multiple paths at once."""
        # Create test files
        clean_file = tmp_path / "clean.md"
        clean_file.write_text("# Heading\n\n## Section\n")

        violation_file = tmp_path / "violations.md"
        violation_file.write_text("# H1\n\n### H3\n")  # Skips H2

        linter = Linter()
        result = linter.lint_paths([clean_file, violation_file])

        assert result.files_checked == 2
        assert result.files_with_violations >= 1

    def test_lint_paths_directory(self, tmp_path: Path) -> None:
        """Lint a directory discovers all markdown files."""
        # Create nested structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        (tmp_path / "root.md").write_text("# Root\n")
        (subdir / "nested.md").write_text("# Nested\n")

        linter = Linter()
        result = linter.lint_paths([tmp_path])

        assert result.files_checked == 2

    def test_violations_sorted_by_line_and_column(self) -> None:
        """Violations are sorted by line then column."""
        linter = Linter()
        # Content with multiple violations on different lines
        content = "# H1\n\n### H3\n\n##### H5\n"

        result = linter.lint_file(Path("test.md"), content=content)

        if len(result.violations) >= 2:
            for i in range(len(result.violations) - 1):
                v1, v2 = result.violations[i], result.violations[i + 1]
                assert (v1.line, v1.column) <= (v2.line, v2.column)


class TestLinterSuppression:
    """Tests for inline suppression through the linter."""

    def test_disable_range_suppresses_violations(self) -> None:
        """Violations in a disable/enable range are suppressed."""
        linter = Linter()
        path = fixture_path("suppression", "disable_range.md")

        result = linter.lint_file(path)

        md001_violations = [v for v in result.violations if v.rule_id == "MD001"]
        assert len(md001_violations) == 0

    def test_disable_next_line_suppresses_one_line(self) -> None:
        """disable-next-line only suppresses the next line."""
        linter = Linter()
        path = fixture_path("suppression", "disable_next_line.md")

        result = linter.lint_file(path)

        md001_violations = [v for v in result.violations if v.rule_id == "MD001"]
        # Line 4 (### Skipped heading) is suppressed, but line 6 (##### Should still trigger) is not
        assert len(md001_violations) == 1
        assert md001_violations[0].line == 6

    def test_blanket_disable_suppresses_all(self) -> None:
        """Blanket disable suppresses all rules."""
        linter = Linter()
        path = fixture_path("suppression", "blanket_disable.md")

        result = linter.lint_file(path)

        # Lines 6 and 8 are inside the blanket disable region
        suppressed_lines = {6, 8}
        for v in result.violations:
            assert v.line not in suppressed_lines

    def test_directive_in_code_block_ignored(self) -> None:
        """Directives inside code blocks have no effect."""
        linter = Linter()
        path = fixture_path("suppression", "code_block.md")

        result = linter.lint_file(path)

        md001_violations = [v for v in result.violations if v.rule_id == "MD001"]
        assert len(md001_violations) == 1

    def test_suppression_comments_exempt_from_md033(self) -> None:
        """Suppression comments should not trigger MD033."""
        linter = Linter()
        content = "# Heading\n\n<!-- mdlint: disable MD001 -->\n\n### Skip\n"

        result = linter.lint_file(Path("test.md"), content=content)

        md033_on_directive = [v for v in result.violations if v.rule_id == "MD033" and v.line == 3]
        assert len(md033_on_directive) == 0


class TestDiscoverFiles:
    """Tests for discover_files function."""

    def test_discover_single_md_file(self, tmp_path: Path) -> None:
        """Single .md file is discovered."""
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test")

        files = discover_files([md_file])

        assert len(files) == 1
        assert files[0] == md_file

    def test_discover_non_md_file_excluded(self, tmp_path: Path) -> None:
        """Non-markdown files are excluded."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("# Test")

        files = discover_files([txt_file])

        assert len(files) == 0

    def test_discover_directory_only_md_files(self, tmp_path: Path) -> None:
        """Directory discovery only includes .md files."""
        (tmp_path / "doc.md").write_text("# Doc")
        (tmp_path / "readme.MD").write_text("# Readme")  # Uppercase extension
        (tmp_path / "notes.txt").write_text("Notes")
        (tmp_path / "script.py").write_text("print('hi')")

        files = discover_files([tmp_path])

        assert len(files) == 2
        filenames = {f.name for f in files}
        assert filenames == {"doc.md", "readme.MD"}

    def test_discover_nested_directories(self, tmp_path: Path) -> None:
        """Nested directories are traversed."""
        (tmp_path / "root.md").write_text("# Root")

        level1 = tmp_path / "level1"
        level1.mkdir()
        (level1 / "l1.md").write_text("# Level 1")

        level2 = level1 / "level2"
        level2.mkdir()
        (level2 / "l2.md").write_text("# Level 2")

        files = discover_files([tmp_path])

        assert len(files) == 3

    def test_discover_empty_directory(self, tmp_path: Path) -> None:
        """Empty directory returns no files."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        files = discover_files([empty_dir])

        assert len(files) == 0

    def test_discover_multiple_paths(self, tmp_path: Path) -> None:
        """Multiple paths can be specified."""
        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        (dir1 / "a.md").write_text("# A")

        dir2 = tmp_path / "dir2"
        dir2.mkdir()
        (dir2 / "b.md").write_text("# B")

        files = discover_files([dir1, dir2])

        assert len(files) == 2

    def test_discover_deduplicates_files(self, tmp_path: Path) -> None:
        """Same file specified multiple times is deduplicated."""
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test")

        files = discover_files([md_file, md_file, tmp_path])

        assert len(files) == 1

    def test_discover_returns_sorted_files(self, tmp_path: Path) -> None:
        """Files are returned in sorted order."""
        (tmp_path / "z.md").write_text("# Z")
        (tmp_path / "a.md").write_text("# A")
        (tmp_path / "m.md").write_text("# M")

        files = discover_files([tmp_path])

        filenames = [f.name for f in files]
        assert filenames == sorted(filenames)

    def test_discover_respects_gitignore(self, tmp_path: Path) -> None:
        """Files in .gitignore are excluded by default."""
        # Initialize git repo and create .gitignore
        os.system(f"git init {tmp_path} --quiet")
        (tmp_path / ".gitignore").write_text("ignored/\n")

        (tmp_path / "included.md").write_text("# Included")

        ignored_dir = tmp_path / "ignored"
        ignored_dir.mkdir()
        (ignored_dir / "excluded.md").write_text("# Excluded")

        files = discover_files([tmp_path], respect_gitignore=True)

        filenames = {f.name for f in files}
        assert "included.md" in filenames
        assert "excluded.md" not in filenames

    def test_discover_exclude_file_pattern(self, tmp_path: Path) -> None:
        """Exclude files matching a filename glob pattern."""
        (tmp_path / "keep.md").write_text("# Keep")
        (tmp_path / "draft.tmp.md").write_text("# Draft")

        files = discover_files([tmp_path], exclude_patterns=["*.tmp.md"])

        filenames = {f.name for f in files}
        assert "keep.md" in filenames
        assert "draft.tmp.md" not in filenames

    def test_discover_exclude_directory_path(self, tmp_path: Path) -> None:
        """Exclude files inside a directory by path."""
        (tmp_path / "root.md").write_text("# Root")
        vendor = tmp_path / "vendor"
        vendor.mkdir()
        (vendor / "lib.md").write_text("# Lib")

        files = discover_files([tmp_path], exclude_patterns=[str(vendor)])

        filenames = {f.name for f in files}
        assert "root.md" in filenames
        assert "lib.md" not in filenames

    def test_discover_exclude_multiple_patterns(self, tmp_path: Path) -> None:
        """Multiple exclude patterns are all applied."""
        (tmp_path / "keep.md").write_text("# Keep")
        (tmp_path / "draft.tmp.md").write_text("# Draft")
        vendor = tmp_path / "vendor"
        vendor.mkdir()
        (vendor / "lib.md").write_text("# Lib")

        files = discover_files([tmp_path], exclude_patterns=["*.tmp.md", str(vendor)])

        filenames = {f.name for f in files}
        assert filenames == {"keep.md"}

    def test_discover_no_ignore_includes_gitignored(self, tmp_path: Path) -> None:
        """With respect_gitignore=False, gitignored files are included."""
        # Initialize git repo and create .gitignore
        os.system(f"git init {tmp_path} --quiet")
        (tmp_path / ".gitignore").write_text("ignored/\n")

        (tmp_path / "included.md").write_text("# Included")

        ignored_dir = tmp_path / "ignored"
        ignored_dir.mkdir()
        (ignored_dir / "excluded.md").write_text("# Excluded")

        files = discover_files([tmp_path], respect_gitignore=False)

        filenames = {f.name for f in files}
        assert "included.md" in filenames
        assert "excluded.md" in filenames
