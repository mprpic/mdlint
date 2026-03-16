import fnmatch
import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path

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
    was_fixed: bool = False


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
    def files_fixed(self) -> int:
        """Files where fixes were applied."""
        return sum(1 for f in self.files if f.was_fixed)

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
    from ignore import WalkBuilder  # noqa: PLC0415

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


def _process_file_worker(
    path: Path,
    rule_configs: dict[str, RuleConfig],
    enabled_rules: set[str],
    *,
    fix: bool,
) -> FileResult:
    """Worker function for parallel file processing. Must be top-level for pickling."""
    linter = Linter(rule_configs=rule_configs, enabled_rules=enabled_rules)
    return linter.fix_file(path) if fix else linter.lint_file(path)


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

    def lint_file(
        self, path: Path, content: str | None = None, document: Document | None = None
    ) -> FileResult:
        """Lint a single file.

        Args:
            path: File path.
            content: Optional content (if already read, e.g., stdin).
            document: Optional pre-parsed document to avoid re-parsing.

        Returns:
            FileResult with violations or error.
        """
        try:
            if content is None:
                content = path.read_text(encoding="utf-8")

            if document is None:
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

    def fix_file(self, path: Path, content: str | None = None) -> FileResult:
        """Fix and lint a single file.

        Applies fixable rules sequentially, writes back if changed, then
        collects remaining violations from all rules.

        Args:
            path: File path.
            content: Optional content (if already read, e.g., stdin).

        Returns:
            FileResult with remaining violations and was_fixed flag.
        """
        try:
            if content is None:
                content = path.read_text(encoding="utf-8")

            was_fixed = False
            document = Document(path, content)

            # Cache check() results from the fix loop. When content changes,
            # the cache is invalidated so only results checked against the
            # final document are reused in the violation-collection pass below.
            cached_violations: dict[str, list[Violation]] = {}

            for rule, config in self._rules:
                if not rule.fixable:
                    continue

                violations = rule.check(document, config)
                cached_violations[rule.id] = violations
                if not violations:
                    continue

                # Skip fix if all violations for this rule are suppressed
                non_suppressed = filter_suppressed(document, violations)
                if not non_suppressed:
                    continue

                fixed = rule.fix(document, config)
                if fixed is not None:
                    content = fixed
                    document = Document(path, content)
                    cached_violations.clear()
                    was_fixed = True

            if was_fixed and path != Path("<stdin>"):
                path.write_text(content, encoding="utf-8")

            # Collect final violations from all rules, reusing cached results
            # for fixable rules already checked against the final document.
            violations: list[Violation] = []
            for rule, config in self._rules:
                if rule.id in cached_violations:
                    violations.extend(cached_violations[rule.id])
                else:
                    violations.extend(rule.check(document, config))

            violations = filter_suppressed(document, violations)
            violations.sort(key=lambda v: (v.line, v.column))

            result = FileResult(path=path, violations=violations, content=content)
            result.was_fixed = was_fixed
            return result

        except OSError as e:
            return FileResult(path=path, error=str(e))

    def fix_stdin(self, content: str) -> tuple[FileResult, str]:
        """Fix content from stdin.

        Args:
            content: Content read from stdin.

        Returns:
            Tuple of (FileResult with remaining violations, fixed content).
        """
        result = self.fix_file(Path("<stdin>"), content=content)
        return result, result.content or content

    def fix_paths(
        self,
        paths: list[Path],
        respect_gitignore: bool = True,
        exclude_patterns: list[str] | None = None,
    ) -> LintResult:
        """Fix and lint multiple files or directories.

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
        return self._process_files(files, fix=True)

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
        return self._process_files(files, fix=False)

    _PARALLEL_THRESHOLD = 64

    def _process_files(self, files: list[Path], *, fix: bool) -> LintResult:
        process_fn = self.fix_file if fix else self.lint_file
        workers = min(os.cpu_count() or 1, len(files))

        if workers < 2 or len(files) < self._PARALLEL_THRESHOLD:
            return LintResult(files=[process_fn(f) for f in files])

        enabled_rules = set(rule.id for rule, _ in self._rules)
        worker = partial(
            _process_file_worker,
            rule_configs=self.rule_configs,
            enabled_rules=enabled_rules,
            fix=fix,
        )
        with ProcessPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(worker, files))
        return LintResult(files=results)
