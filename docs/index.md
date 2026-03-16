---
hide:
  - toc
---

# mdlint

mdlint is a Python Markdown linter that checks files for style and formatting violations. It helps maintain consistent
Markdown in your code base or documentation project.

## Features

- **50+ built-in rules** covering headings, lists, whitespace, links, code blocks, etc.
- **Configurable** via `.mdlint.toml` or `pyproject.toml` with per-rule customization
- **Multiple output formats** including human-readable terminal output and JSON
- **Gitignore-aware** file discovery that respects `.gitignore`/`.ignore` patterns
- **Auto-fix support** via `--fix` to automatically correct fixable violations
- **stdin support** for integration with editors and or use in CI pipelines
- **Built-in rule documentation** accessible from the CLI, with valid/invalid examples
- **[Online playground](playground.md)** to try mdlint directly in the browser — no installation needed
- **Parallel processing** of files automatically when checking large projects
- **Compatible** (mostly) with existing `markdownlint` rule sets (Ruby and JavaScript implementations)

## Quick start

Install mdlint:

```bash
uv tool install --from git+https://github.com/mprpic/mdlint mdlint
```

Lint a file:

```bash
mdlint check README.md
```

Lint all Markdown files in a directory:

```bash
mdlint check docs/
```

View available rules:

```bash
mdlint rule
```
