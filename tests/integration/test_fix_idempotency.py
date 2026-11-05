import pytest

from mdlint.linter import Linter
from tests.conftest import FIXTURES_DIR

FIXTURES = sorted(FIXTURES_DIR.rglob("*.md"))


@pytest.mark.parametrize(
    "path", FIXTURES, ids=lambda path: path.relative_to(FIXTURES_DIR).as_posix()
)
def test_fix_is_idempotent(path) -> None:
    """A second --fix run must find nothing left to change.

    Otherwise users see a different file each time they run --fix, and a fix that keeps
    adding lines grows the file on every run (for example in a pre-commit hook).
    """
    linter = Linter()
    content = path.read_bytes().decode("utf-8")

    _, once = linter.fix_stdin(content)
    _, twice = linter.fix_stdin(once)

    assert twice.count("\n") <= once.count("\n"), "second run added lines"
    assert twice == once
