from pathlib import Path

import pytest

from mdlint.document import Document
from mdlint.rules.md040 import MD040, MD040Config
from tests.conftest import load_fixture


class TestMD040:
    @pytest.fixture
    def rule(self) -> MD040:
        return MD040()

    @pytest.fixture
    def config(self) -> MD040Config:
        return MD040Config()

    def test_valid_document(self, rule: MD040, config: MD040Config) -> None:
        """Valid document with language specified on all fenced code blocks."""
        content = load_fixture("md040", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_invalid_document(self, rule: MD040, config: MD040Config) -> None:
        """Invalid document with missing language on fenced code block."""
        content = load_fixture("md040", "invalid.md")
        doc = Document(Path("invalid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].rule_id == "MD040"
        assert violations[0].line == 5
        assert "language" in violations[0].message.lower()

    def test_no_code_blocks(self, rule: MD040, config: MD040Config) -> None:
        """Document without any code blocks passes."""
        content = load_fixture("md040", "no_code_blocks.md")
        doc = Document(Path("no_code_blocks.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_multiple_missing_languages(self, rule: MD040, config: MD040Config) -> None:
        """Multiple code blocks without languages."""
        content = load_fixture("md040", "multiple_missing.md")
        doc = Document(Path("multiple_missing.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 2
        assert violations[0].line == 5
        assert violations[1].line == 11

    def test_allowed_languages_valid(self, rule: MD040) -> None:
        """Code blocks with allowed languages pass."""
        config = MD040Config(allowed_languages=["python", "javascript"])
        content = load_fixture("md040", "allowed_languages.md")
        doc = Document(Path("allowed_languages.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_allowed_languages_violation(self, rule: MD040) -> None:
        """Code block with disallowed language triggers violation."""
        config = MD040Config(allowed_languages=["python", "javascript"])
        content = load_fixture("md040", "disallowed_language.md")
        doc = Document(Path("disallowed_language.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3
        assert "ruby" in violations[0].message

    def test_language_only_valid(self, rule: MD040) -> None:
        """Language only mode with just language identifier passes."""
        config = MD040Config(language_only=True)
        content = load_fixture("md040", "valid.md")
        doc = Document(Path("valid.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_language_only_violation(self, rule: MD040) -> None:
        """Language only mode with extra metadata triggers violation."""
        config = MD040Config(language_only=True)
        content = load_fixture("md040", "language_with_metadata.md")
        doc = Document(Path("language_with_metadata.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3
        assert (
            "only" in violations[0].message.lower() or "metadata" in violations[0].message.lower()
        )

    def test_indented_code_block_ignored(self, rule: MD040, config: MD040Config) -> None:
        """Indented code blocks are ignored (only fenced blocks checked)."""
        content = load_fixture("md040", "indented_code_block.md")
        doc = Document(Path("indented_code_block.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 0

    def test_tilde_fence_without_language(self, rule: MD040, config: MD040Config) -> None:
        """Tilde-fenced code blocks without language trigger a violation."""
        content = load_fixture("md040", "tilde_fence.md")
        doc = Document(Path("tilde_fence.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3
        assert "language" in violations[0].message.lower()

    def test_allowed_languages_with_language_only(self, rule: MD040) -> None:
        """Allowed language with extra metadata triggers language_only violation."""
        config = MD040Config(allowed_languages=["python"], language_only=True)
        content = load_fixture("md040", "allowed_with_metadata.md")
        doc = Document(Path("allowed_with_metadata.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3
        assert "metadata" in violations[0].message.lower()

    def test_whitespace_only_info_string(self, rule: MD040, config: MD040Config) -> None:
        """Fence with whitespace-only info string is treated as missing language."""
        content = load_fixture("md040", "whitespace_info.md")
        doc = Document(Path("whitespace_info.md"), content)

        violations = rule.check(doc, config)

        assert len(violations) == 1
        assert violations[0].line == 3
        assert "language" in violations[0].message.lower()
