---
hide:
  - toc
---

# Installation

`mdlint` requires Python 3.10 or later.

<!-- mdlint: disable MD046 -->
=== "uv"

    Install as a [uv tool](https://docs.astral.sh/uv/guides/tools/):

    ```bash
    uv tool install mdlint
    ```

    Or run directly in a temporary environment without installing:

    ```bash
    uvx mdlint check README.md
    ```

=== "pip"

    Install from PyPI:

    ```bash
    pip install --user mdlint
    ```
