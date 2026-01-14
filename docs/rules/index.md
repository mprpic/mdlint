---
hide:
  - toc
---

# Rules

## Rule Compatibility Matrix

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

## Available Rules

This is a list of all available rules.
