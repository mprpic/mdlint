import pytest

from mdlint.rules import resolve_rule_id


class TestResolveRuleId:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("MD013", "MD013"),
            ("md013", "MD013"),
            ("line-length", "MD013"),
            ("Line-Length", "MD013"),
            ("  MD001 ", "MD001"),
            ("no-inline-html", "MD033"),
        ],
    )
    def test_known(self, name: str, expected: str) -> None:
        assert resolve_rule_id(name) == expected

    @pytest.mark.parametrize("name", ["MD002", "MD999", "not-a-rule", "", "MD01"])
    def test_unknown(self, name: str) -> None:
        assert resolve_rule_id(name) is None
