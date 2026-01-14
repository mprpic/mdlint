from pathlib import Path

# Path to test fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def fixture_path(rule_id: str, filename: str) -> Path:
    """Get path to a specific fixture file.

    Args:
        rule_id: Rule ID (e.g., "md001").
        filename: Fixture filename (e.g., "valid.md").

    Returns:
        Path to the fixture file.
    """
    return FIXTURES_DIR / rule_id.lower() / filename


def load_fixture(rule_id: str, filename: str) -> str:
    """Load fixture file content.

    Args:
        rule_id: Rule ID (e.g., "md001").
        filename: Fixture filename (e.g., "valid.md").

    Returns:
        Content of the fixture file.
    """
    return fixture_path(rule_id, filename).read_text(encoding="utf-8")
