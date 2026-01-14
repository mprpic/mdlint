import fnmatch
from dataclasses import dataclass, field
from pathlib import Path

from ignore import WalkBuilder

from mdlint.document import Document
from mdlint.rules import RULE_REGISTRY
from mdlint.rules.base import Rule, RuleConfig
from mdlint.suppression import filter_suppressed
from mdlint.violation import Violation


@dataclass
class FileResult:
    """Aggregates violations for a single file.

    Attributes:
        path: File path.
        violations: All violations found.
        error: Error message if file couldn't be read.
        content: File content for context display.
    """

    path: Path
    violations: list[Violation] = field(default_factory=list)
    error: str | None = None
    content: str | None = None


@dataclass
class LintResult:
    """Aggregates results across all files.

    Attributes:
        files: Results per file.
    """

    files: list[FileResult] = field(default_factory=list)

    @property
    def files_checked(self) -> int:
        """Total files processed."""
        return len(self.files)

    @property
    def files_with_violations(self) -> int:
        """Files with at least one violation."""
        return sum(1 for f in self.files if f.violations)

    @property
    def files_with_errors(self) -> int:
        """Files that couldn't be processed."""
        return sum(1 for f in self.files if f.error)

    @property
    def total_violations(self) -> int:
        """Sum of all violations."""
        return sum(len(f.violations) for f in self.files)

    @property
    def exit_code(self) -> int:
        """Exit code based on results.

        Returns:
            0: No violations, no errors.
            1: Violations found (with or without errors).
            2: Errors only (no violations).
        """
        if self.total_violations > 0:
            return 1
        if self.files_with_errors > 0:
            return 2
        return 0


def discover_files(
    paths: list[Path],
    respect_gitignore: bool = True,
    exclude_patterns: list[str] | None = None,
) -> list[Path]:
    """Discover Markdown files from given paths.

    Args:
        paths: List of file or directory paths.
        respect_gitignore: Whether to respect ignore patterns.
        exclude_patterns: Glob patterns to exclude files/directories.

    Returns:
        List of Markdown file paths.
    """
    files: list[Path] = []

    walker = WalkBuilder(paths[0])
    for path in paths[1:]:
        walker.add(path)

    if not respect_gitignore:
        walker.git_ignore(False)
        walker.git_global(False)
        walker.git_exclude(False)
        walker.ignore(False)
        walker.hidden(False)

    for entry in walker.build():
        path = Path(entry.path())
        if path.is_file() and path.suffix.lower() == ".md":
            files.append(path)

    if exclude_patterns:
        filtered = []
        for f in files:
            excluded = False
            resolved_f = f.resolve()
            for pattern in exclude_patterns:
                p = Path(pattern)
                if p.is_dir():
                    if resolved_f.is_relative_to(p.resolve()):
                        excluded = True
                        break
                elif p.is_file():
                    if resolved_f == p.resolve():
                        excluded = True
                        break
                else:
                    # Treat as glob pattern
                    if fnmatch.fnmatch(str(f), pattern):
                        excluded = True
                        break
                    if any(fnmatch.fnmatch(part, pattern) for part in f.parts):
                        excluded = True
                        break
            if not excluded:
                filtered.append(f)
        files = filtered

    return sorted(set(files))


class Linter:
    """Main linter class for checking files."""

    def __init__(
        self,
        rule_configs: dict[str, RuleConfig] | None = None,
        enabled_rules: set[str] | None = None,
    ) -> None:
        """Initialize linter.

        Args:
            rule_configs: Optional mapping of rule ID to config.
            enabled_rules: Set of rule IDs to run. If None, runs all rules.
        """
        self.rule_configs = rule_configs or {}
        self._rules: list[tuple[Rule, RuleConfig]] = []

        # Default to all rules if not specified
        if enabled_rules is None:
            enabled_rules = set(RULE_REGISTRY.keys())

        # Instantiate enabled rules with their configs
        for rule_id, rule_class in RULE_REGISTRY.items():
            if rule_id in enabled_rules:
                config = self.rule_configs.get(rule_id, rule_class.config_class())
                rule = rule_class()
                self._rules.append((rule, config))

    def lint_file(self, path: Path, content: str | None = None) -> FileResult:
        """Lint a single file.

        Args:
            path: File path.
            content: Optional content (if already read, e.g., stdin).

        Returns:
            FileResult with violations or error.
        """
        try:
            if content is None:
                content = path.read_text(encoding="utf-8")

            document = Document(path, content)
            violations: list[Violation] = []

            for rule, config in self._rules:
                violations.extend(rule.check(document, config))

            violations = filter_suppressed(document, violations)

            # Sort violations by line number
            violations.sort(key=lambda v: (v.line, v.column))

            return FileResult(path=path, violations=violations, content=content)

        except OSError as e:
            return FileResult(path=path, error=str(e))

    def lint_stdin(self, content: str) -> FileResult:
        """Lint content from stdin.

        Args:
            content: Content read from stdin.

        Returns:
            FileResult with violations.
        """
        return self.lint_file(Path("<stdin>"), content=content)

    def lint_paths(
        self,
        paths: list[Path],
        respect_gitignore: bool = True,
        exclude_patterns: list[str] | None = None,
    ) -> LintResult:
        """Lint multiple files or directories.

        Args:
            paths: List of file or directory paths.
            respect_gitignore: Whether to respect .gitignore patterns.
            exclude_patterns: Glob patterns to exclude files/directories.

        Returns:
            Aggregated LintResult.
        """
        files = discover_files(
            paths, respect_gitignore=respect_gitignore, exclude_patterns=exclude_patterns
        )
        results: list[FileResult] = []

        for file_path in files:
            results.append(self.lint_file(file_path))

        return LintResult(files=results)
