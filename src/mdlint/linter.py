import fnmatch
import os
import re
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path

from mdlint.document import Document
from mdlint.rules import RULE_REGISTRY
from mdlint.rules.base import Rule, RuleConfig
from mdlint.suppression import filter_suppressed
from mdlint.violation import Violation

MARKDOWN_EXTENSIONS = frozenset({".md", ".markdown", ".mdown", ".mkd", ".mkdn"})

# Upper bound on fix passes per file; see Linter.fix_file().
MAX_FIX_PASSES = 10

_BOM = "\ufeff"
_LINE_ENDING = re.compile(r"\r\n?|\n")


def _split_encoding(text: str) -> tuple[str, str, str]:
    """Separate a leading BOM and the line-ending style from the text that rules see.

    Rules and markdown-it expect "\\n"-separated lines and would read a BOM as content (so a
    first-line heading is not seen as one). Fixes put both back on write, so the only changes
    to a file are the ones rules made.

    Returns:
        Tuple of (bom, newline, text): bom is "" or U+FEFF, newline is the first line ending
        found ("\\n" if there is none), and text has every line ending replaced by "\\n".
    """
    bom = _BOM if text.startswith(_BOM) else ""
    match = _LINE_ENDING.search(text)
    newline = match.group() if match else "\n"
    return bom, newline, _LINE_ENDING.sub("\n", text[len(bom) :])


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
        paths: List of file or directory paths. Files given here are always included (callers
            such as pre-commit pass Markdown files of any extension); directories are searched
            for files with an extension in MARKDOWN_EXTENSIONS.
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
        # Depth 0 entries are the paths given by the caller.
        if path.is_file() and (entry.depth() == 0 or path.suffix.lower() in MARKDOWN_EXTENSIONS):
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
                content = path.read_bytes().decode("utf-8")
            _, _, content = _split_encoding(content)

            if document is None:
                document = Document(path, content)

            violations: list[Violation] = []

            for rule, config in self._rules:
                violations.extend(rule.check(document, config))

            violations = filter_suppressed(document, violations)

            # Sort violations by line number
            violations.sort(key=lambda v: (v.line, v.column))

            return FileResult(path=path, violations=violations, content=content)

        except (OSError, UnicodeDecodeError) as e:
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

        Fixable rules run in passes, and a pass is repeated because one rule's fix can create
        work for a rule that already ran. Every pass after the first must reduce the number of
        unsuppressed violations of fixable rules or it is discarded: this stops fixes that never
        resolve their own violation from growing the file on each pass, and since the count is
        a function of the content, a strictly decreasing count also rules out cycles. At most
        MAX_FIX_PASSES passes run. The result is written back if it changed, then remaining
        violations are collected from all rules.

        Args:
            path: File path.
            content: Optional content (if already read, e.g., stdin).

        Returns:
            FileResult with remaining violations and was_fixed flag.
        """
        try:
            if content is None:
                content = path.read_bytes().decode("utf-8")
            bom, newline, original = _split_encoding(content)

            fixable = [(rule, config) for rule, config in self._rules if rule.fixable]
            document = Document(path, original)

            # check() results for `document`, reused by the next pass and by the final
            # violation collection below. Each pass fills its own copy so that discarding
            # the pass leaves results that match the kept document.
            cached_violations: dict[str, list[Violation]] = {}
            remaining = self._count_unsuppressed(document, fixable, cached_violations)

            for pass_number in range(MAX_FIX_PASSES):
                if remaining == 0:
                    break
                pass_cache = dict(cached_violations)
                fixed = self._fix_pass(document, fixable, pass_cache)
                if fixed.content == document.content:
                    break
                fixed_remaining = self._count_unsuppressed(fixed, fixable, pass_cache)
                if pass_number > 0 and fixed_remaining >= remaining:
                    break
                document, cached_violations, remaining = fixed, pass_cache, fixed_remaining

            content = document.content
            was_fixed = content != original
            if was_fixed and path != Path("<stdin>"):
                path.write_text(bom + content.replace("\n", newline), encoding="utf-8", newline="")

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

        except (OSError, UnicodeDecodeError) as e:
            return FileResult(path=path, error=str(e))

    @staticmethod
    def _count_unsuppressed(
        document: Document,
        fixable: list[tuple[Rule, RuleConfig]],
        cached_violations: dict[str, list[Violation]],
    ) -> int:
        """Measure how much fixing is left, to decide whether a fix pass made progress.

        Fills `cached_violations` (which must only hold results for `document`) as a side
        effect, so the next pass or the final collection does not re-run these checks.
        """
        violations: list[Violation] = []
        for rule, config in fixable:
            if rule.id not in cached_violations:
                cached_violations[rule.id] = rule.check(document, config)
            violations.extend(cached_violations[rule.id])
        return len(filter_suppressed(document, violations))

    @staticmethod
    def _fix_pass(
        document: Document,
        fixable: list[tuple[Rule, RuleConfig]],
        cached_violations: dict[str, list[Violation]],
    ) -> Document:
        """Apply each fixable rule's fix once, in registry order.

        `cached_violations` must only hold check() results for `document`; it is updated in
        place to hold results for the returned document.
        """
        for rule, config in fixable:
            if rule.id not in cached_violations:
                cached_violations[rule.id] = rule.check(document, config)
            violations = cached_violations[rule.id]
            if not violations:
                continue

            # fix() rewrites the whole document and its edits depend on each other (both
            # fences of one block, say), so it cannot be applied around a suppressed
            # violation. A rule with a suppressed violation is left unfixed in this file.
            unsuppressed = filter_suppressed(document, violations)
            if not unsuppressed or len(unsuppressed) < len(violations):
                continue

            fixed = rule.fix(document, config)
            if fixed is not None and fixed != document.content:
                document = Document(document.path, fixed)
                cached_violations.clear()

        return document

    def fix_stdin(self, content: str) -> tuple[FileResult, str]:
        """Fix content from stdin.

        Args:
            content: Content read from stdin.

        Returns:
            Tuple of (FileResult with remaining violations, fixed content).
        """
        result = self.fix_file(Path("<stdin>"), content=content)
        if result.content is None:
            return result, content
        bom, newline, _ = _split_encoding(content)
        return result, bom + result.content.replace("\n", newline)

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
