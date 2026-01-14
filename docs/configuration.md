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

Configuration is resolved in the following order (highest to lowest priority):

1. Command-line options (`--config`, `--select`, `--ignore`, etc.)
2. `.mdlint.toml` in the project root
3. `pyproject.toml` under `[tool.mdlint]`
4. Rule defaults

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
mdlint check --ignore MD002

# Add to existing select/ignore lists
mdlint check --extend-select MD004 --extend-ignore MD005
```
