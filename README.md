# mdlint

A Python Markdown linter that checks files for style and formatting violations.

- **50+ built-in rules** covering headings, lists, whitespace, links, code blocks, and more
- **Configurable** via `.mdlint.toml` or `pyproject.toml` with per-rule settings
- **Multiple output formats** including human-readable terminal output and JSON
- **Gitignore-aware** file discovery that respects `.gitignore` patterns
- **stdin support** for integration with editors and CI pipelines
- **Built-in rule documentation** accessible from the CLI
- **[Online playground](https://mdlint.dev/playground/)** to try mdlint directly in the browser — no installation needed
- **Compatible** with existing `markdownlint` rule sets (Ruby and JavaScript implementations)

## Installation

```bash
uv tool install --from git+https://github.com/mprpic/mdlint mdlint
# OR
pip install --user git+https://github.com/mprpic/mdlint
# OR run directly
uvx --from git+https://github.com/mprpic/mdlint mdlint -h
```

Requires Python 3.10 or later.

## Usage

### Lint files or directories

```bash
# Lint current directory
mdlint check

# Lint specific files
mdlint check README.md docs/guide.md

# Lint a directory recursively
mdlint check docs/

# Lint from stdin
cat README.md | mdlint check -
```

### Output formats

```bash
# Human-readable output (default)
mdlint check docs/

# JSON output
mdlint check --format json docs/
```

### View rule documentation

```bash
# List all rules
mdlint rule

# View specific rule details
mdlint rule MD001

# Include valid/invalid examples
mdlint rule MD003 --show-examples
```

## Rule compatibility matrix

The following table shows rule availability across mdlint and the
[Ruby](https://github.com/markdownlint/markdownlint) and
[JavaScript](https://github.com/DavidAnson/markdownlint) `markdownlint` implementations. The rule behavior is mostly
consistent with that of the `markdownlint` projects (slight preference to the JavaScript implementation), but may differ
slightly over time as the project evolves.

| Rule(s)     | mdlint | Ruby markdownlint | JS markdownlint | Notes                       |
|-------------|:------:|:-----------------:|:---------------:|-----------------------------|
| MD001       |   ✓    |         ✓         |        ✓        |                             |
| MD002       |   —    |         ✓         |        —        | Not implemented (use MD041) |
| MD003–MD005 |   ✓    |         ✓         |        ✓        |                             |
| MD006       |   —    |         ✓         |        —        | Not implemented (use MD007) |
| MD007       |   ✓    |         ✓         |        ✓        |                             |
| MD008       |   —    |         —         |        —        | Not implemented             |
| MD009–MD014 |   ✓    |         ✓         |        ✓        |                             |
| MD015–MD017 |   —    |         —         |        —        | Not implemented             |
| MD018–MD041 |   ✓    |         ✓         |        ✓        |                             |
| MD042–MD045 |   ✓    |         —         |        ✓        |                             |
| MD046–MD047 |   ✓    |         ✓         |        ✓        |                             |
| MD048–MD056 |   ✓    |         —         |        ✓        |                             |
| MD057       |   —    |         —         |        —        | Not implemented             |
| MD058–MD060 |   ✓    |         —         |        ✓        |                             |

## Configuration

### Configuration file

Create `.mdlint.toml` in your project root:

```toml
# Select specific rules to run (default: all rules)
select = ["MD001", "MD003", "MD041"]

# Ignore specific rules (subtracted from select)
ignore = ["MD041"]

# Rule-specific configuration
[rules.MD041]
level = 2  # Expect first heading to be h2

[rules.MD003]
style = "atx"  # atx | atx_closed | setext | setext_with_atx | consistent

[rules.MD013]
line_length = 120
code_blocks = false
```

Or add to `pyproject.toml`:

```toml
[tool.mdlint]
ignore = ["MD041"]

[tool.mdlint.rules.MD003]
style = "atx"
```

### Rule selection

The `select` and `ignore` options work together:

- `select` establishes the baseline set of rules (defaults to all rules if omitted)
- `ignore` subtracts from the select set

Examples:

```toml
# Run all rules except MD041
ignore = ["MD041"]
```

```toml
# Run only MD001 and MD003
select = ["MD001", "MD003"]
```

```toml
# Run MD001, MD003-MD005, but skip MD004
select = ["MD001", "MD003", "MD004", "MD005"]
ignore = ["MD004"]  # Alternatively, omit from select list
```

### Command-line options

```bash
# Use a specific config file
mdlint check --config path/to/config.toml

# Inline configuration
mdlint check --config "MD003.style='atx'"

# Select specific rules (replaces config select list)
mdlint check --select MD001 --select MD003

# Ignore specific rules (replaces config ignore list)
mdlint check --ignore MD002

# Add to existing select/ignore lists
mdlint check --extend-select MD004 --extend-ignore MD005

# Disable .gitignore and .ignore patterns
mdlint check --no-ignore

# Verbose output (show files being processed)
mdlint check --verbose
```

## Exit codes

| Code | Meaning                                               |
|------|-------------------------------------------------------|
| 0    | No violations found                                   |
| 1    | Violations found                                      |
| 2    | Error occurred (file not found, invalid config, etc.) |

## Future improvements

- Parallel processing of files (if many are being checked)
- A `--fix` option to auto-fix some violations

## License

MIT
