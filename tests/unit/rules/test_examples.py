"""Tests to verify rule examples match fixture files."""

import pytest

from mdlint.rules import RULE_REGISTRY
from tests.conftest import load_fixture


class TestRuleExamples:
    """Verify that rule example_valid attributes match the valid.md fixtures."""

    @pytest.mark.parametrize(
        "rule_id",
        [
            rule_id
            for rule_id, rule_class in RULE_REGISTRY.items()
            if rule_class.example_valid is not None
        ],
    )
    def test_example_valid_matches_fixture(self, rule_id: str) -> None:
        """Verify example_valid matches the valid.md fixture file."""
        rule_class = RULE_REGISTRY[rule_id]
        fixture_content = load_fixture(rule_id.lower(), "valid.md")

        assert rule_class.example_valid == fixture_content, (
            f"{rule_id}.example_valid does not match tests/fixtures/{rule_id.lower()}/valid.md"
        )

    @pytest.mark.parametrize(
        "rule_id",
        [
            rule_id
            for rule_id, rule_class in RULE_REGISTRY.items()
            if rule_class.example_invalid is not None
        ],
    )
    def test_example_invalid_matches_fixture(self, rule_id: str) -> None:
        """Verify example_invalid matches the invalid.md fixture file."""
        rule_class = RULE_REGISTRY[rule_id]
        fixture_content = load_fixture(rule_id.lower(), "invalid.md")

        assert rule_class.example_invalid == fixture_content, (
            f"{rule_id}.example_invalid does not match tests/fixtures/{rule_id.lower()}/invalid.md"
        )
