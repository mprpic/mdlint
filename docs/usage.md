---
hide:
  - toc
---

# Usage

## Linting files

Lint the current directory (recursively finds all Markdown files):

```bash
mdlint check
```

Lint specific files:

```bash
mdlint check README.md docs/guide.md
```

Lint a directory recursively:

```bash
mdlint check docs/
```

Lint from stdin:

```bash
cat README.md | mdlint check -
```

## Output formats

Human-readable terminal output (default):

```bash
$ mdlint check docs/
docs/usage.md (2)
 6:1  MD041  First heading should be h1, found h2
52:1  MD040  Fenced code block without language specified

✘ Found 2 violations in 1 file (5 files checked)
```

JSON output for programmatic use:

```bash
$ mdlint check --format json docs/
{
  "files": [
    {
      "path": "docs/usage.md",
      "violations": [
        {
          "line": 6,
          "column": 1,
          "rule_id": "MD041",
          "rule_name": "first-line-heading",
          "message": "First heading should be h1, found h2",
          "context": "## Usage"
        },
        {
          "line": 56,
          "column": 1,
          "rule_id": "MD040",
          "rule_name": "fenced-code-language",
          "message": "Fenced code block without language specified",
          "context": "```"
        }
      ],
      "error": null
    }
  ],
  "summary": {
    "files_checked": 5,
    "files_with_violations": 1,
    "files_with_errors": 0,
    "total_violations": 2,
    "exit_code": 1
  }
}
```

Show the in-file context of the found error:

```bash
$ mdlint check --show-context docs/
docs/usage.md (2)
 6:1  MD041  First heading should be h1, found h2

    4: ---
    5:
    6: ## Usage
       ^
    7:
    8: ## Linting files

88:1  MD040  Fenced code block without language specified

    86: Show the in-file context of the found error:
    87:
    88: ```
        ^
    89: $ mdlint check --show-context docs/
    90: docs/usage.md (2)


✘ Found 2 violations in 1 file (5 files checked)
```

## Additional options

```bash
# Disable .gitignore and .ignore patterns
mdlint check --no-ignore

# Show files being processed
mdlint check --verbose

# List files that would be linted without linting them
mdlint check --show-files
```

## Auto-fixing violations

Use `--fix` to automatically correct fixable violations:

```bash
# Fix violations in files in-place
mdlint check --fix docs/

# Fix a single file
mdlint check --fix README.md

# Fix stdin and output the result to stdout
cat README.md | mdlint check --fix -
```

Not all rules support auto-fixing. When `--fix` is used:

- Fixable rules are applied sequentially to each file
- Files are modified in-place with the corrected content
- Any remaining unfixable violations are still reported in the output
- The [rules index](rules/index.md) shows which rules are fixable with a checkmark in the "Fixable" column

When used with stdin (`-`), the fixed content is written to stdout. This is useful for editor integrations that pipe
content through external formatters.

The exit code behavior is unchanged: exit code `1` if any violations remain after fixing, `0` if all violations were
fixed or there were none.

## Viewing rule documentation

List all available rules:

```bash
mdlint rule
```

View details for a specific rule:

```bash
mdlint rule MD001
```

Include valid/invalid examples:

```bash
mdlint rule MD003 --show-examples
```

## Inline suppression

You can suppress specific rule violations inline using HTML comment directives (ignored inside code blocks). This is
useful when a violation is intentional, and you don't want to disable the rule globally.

Suppress one or more rules from a specific point until re-enabled:

```markdown
<!-- mdlint: disable MD013 -->

This long line (if it were long enough) will not trigger MD013.

<!-- mdlint: enable MD013 -->
```

```markdown
<!-- mdlint: disable MD001 MD013 -->
...
<!-- mdlint: enable -->
```

Unknown rule IDs are silently ignored.

You can selectively re-enable specific rules after a disable comment:

```markdown
<!-- mdlint: disable -->
<!-- mdlint: enable MD001 -->

### MD001 still applies here, but other rules are suppressed.

<!-- mdlint: enable -->
```

Suppress one or more rules for just the line immediately following the comment:

```markdown
<!-- mdlint: disable-next-line MD001 -->

### This heading won't trigger MD001
```

Suppression comments are automatically exempt from triggering MD033 (`no-inline-html`) violations

## Exit codes

| Code | Meaning                                               |
|------|-------------------------------------------------------|
| 0    | No violations found                                   |
| 1    | Violations found                                      |
| 2    | Error occurred (file not found, invalid config, etc.) |
