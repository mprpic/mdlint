import re
from dataclasses import dataclass

from mdlint.document import Document
from mdlint.violation import Violation

DIRECTIVE_PATTERN = re.compile(
    r"^\s*<!--\s*mdlint:\s*(disable|enable|disable-next-line)(?:\s+([\w\s]+?))?\s*-->\s*$"
)


@dataclass
class Directive:
    """A parsed suppression directive."""

    line: int  # 1-indexed line number
    kind: str  # "disable", "enable", or "disable-next-line"
    rule_ids: list[str]  # Empty list means all rules


def _parse_directives(document: Document) -> list[Directive]:
    """Parse suppression directives from document lines, skipping code blocks."""
    code_block_lines = document.code_block_lines
    directives: list[Directive] = []

    for line_num, line in enumerate(document.lines, start=1):
        if line_num in code_block_lines:
            continue
        match = DIRECTIVE_PATTERN.match(line)
        if match:
            kind = match.group(1)
            rule_ids = match.group(2).split() if match.group(2) else []
            directives.append(Directive(line=line_num, kind=kind, rule_ids=rule_ids))

    return directives


def _is_suppressed(rule_id: str, line: int, directives: list[Directive]) -> bool:
    """Check if a rule is suppressed at a given line by walking directives in order."""
    disabled_all = False
    disabled_rules: set[str] = set()
    enabled_overrides: set[str] = set()

    for d in directives:
        if d.line > line:
            break

        if d.kind == "disable-next-line":
            if d.line + 1 == line:
                if not d.rule_ids:
                    return True
                if rule_id in d.rule_ids:
                    return True
        elif d.kind == "disable":
            if d.rule_ids:
                disabled_rules.update(d.rule_ids)
                for r in d.rule_ids:
                    enabled_overrides.discard(r)
            else:
                disabled_all = True
                enabled_overrides.clear()
        elif d.kind == "enable":
            if d.rule_ids:
                disabled_rules.difference_update(d.rule_ids)
                if disabled_all:
                    enabled_overrides.update(d.rule_ids)
            else:
                disabled_all = False
                disabled_rules.clear()
                enabled_overrides.clear()

    if rule_id in disabled_rules:
        return True
    if disabled_all and rule_id not in enabled_overrides:
        return True

    return False


def filter_suppressed(document: Document, violations: list[Violation]) -> list[Violation]:
    """Filter out violations that are suppressed by inline directives.

    Also filters MD033 violations that fall on directive comment lines.
    """
    directives = _parse_directives(document)
    if not directives:
        return violations

    directive_lines = {d.line for d in directives}
    # Directives are already sorted by line since we parse in order
    result = []

    for v in violations:
        # Suppress MD033 on directive lines (the comment itself)
        if v.rule_id == "MD033" and v.line in directive_lines:
            continue

        if _is_suppressed(v.rule_id, v.line, directives):
            continue

        result.append(v)

    return result
