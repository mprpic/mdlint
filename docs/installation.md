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
    uv tool install --from git+https://github.com/mprpic/mdlint mdlint
    ```

    Or run directly in a temporary environment without installing:

    ```bash
    uvx --from git+https://github.com/mprpic/mdlint mdlint check README.md
    ```

=== "pip"

    Install directly from GitHub:

    ```bash
    pip install --user git+https://github.com/mprpic/mdlint
    ```
