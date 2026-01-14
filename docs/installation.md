---
hide:
  - toc
---

# Installation

`mdlint` requires Python 3.10 or later.

## Using uv

Install as a [uv tool](https://docs.astral.sh/uv/guides/tools/):

```bash
uv tool install --from git+https://github.com/mprpic/mdlint mdlint
```

Or run directly in a temporary environment without installing:

```bash
uvx --from git+https://github.com/mprpic/mdlint mdlint check README.md
```

## Using pip

```bash
pip install --user git+https://github.com/mprpic/mdlint
```
