---
hide:
  - toc
---

# Configuration

mdlint can be configured via a configuration file or command-line options.

## Configuration file

Create a `.mdlint.toml` file in your project root:

```toml
# Select specific rules to run (default: all rules)
select = ["MD001", "MD003", "MD041"]

# Ignore specific rules (subtracted from select)
ignore = ["MD041"]

# Rule-specific configuration
[rules.MD041]
level = 2  # Expect first heading to be h2

[rules.MD046]
style = "consistent"  # consistent | fenced | indented

[rules.MD013]
line_length = 120
code_blocks = false
```

Or add configuration to `pyproject.toml` under `[tool.mdlint]`:

```toml
[tool.mdlint]
ignore = ["MD041"]

[tool.mdlint.rules.MD003]
style = "atx"
```

Configuration files are discovered in parent directories if not discovered in the directory that the tool is being
run from.

## Precedence

mdlint reads a single configuration file, and settings from different files are never merged:

1. The file (or inline TOML) given with `--config`
2. Otherwise, the first file found by searching from the current directory upward; in each directory, `.mdlint.toml` is
   checked before `pyproject.toml` (which is only used if it has a `[tool.mdlint]` section)
3. Options not set in that file keep their defaults

The `--select`, `--ignore`, `--exclude` options and their `--extend-*` variants are applied on top of that file.

## Rule names

Rules can be referenced by ID or by name, in any case: `MD013`, `md013` and `line-length` are equivalent. This works in
`select` and `ignore`, in `[rules.<rule>]` section names, and in the command-line options.

## Validation

The configuration is checked before any file is linted. mdlint exits with code 2 and a one-line message naming the
config source, rule and option when it finds:

- invalid TOML, or a `--config` path that does not exist
- a top-level key other than `select`, `ignore`, `exclude` and `rules`, such as a misspelled `selct`
- an unknown rule or option (option names use underscores: `line_length`, not `line-length`)
- a value of the wrong type, such as a string where a list is expected (`allowed_elements = ["br", "img"]`, not
  `allowed_elements = "br, img"`)
- a value that is not one of the option's allowed choices (each rule's page lists them)

## Rule selection

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
ignore = ["MD004"]
```

## Command-line options

Configuration can also be provided via command-line options. These take precedence over configuration files.

```bash
# Use a specific config file
mdlint check --config path/to/config.toml

# Inline configuration
mdlint check --config "MD003.style='atx'"

# Select specific rules (replaces config select list)
mdlint check --select MD001 --select MD003

# Ignore specific rules (replaces config ignore list)
mdlint check --ignore MD041

# Add to existing select/ignore lists
mdlint check --extend-select MD004 --extend-ignore MD005
```

A `--config` value that is not an existing file is treated as inline TOML when it contains `=`, and is reported as a
missing file otherwise.
