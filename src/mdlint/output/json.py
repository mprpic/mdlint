import json

from mdlint.linter import LintResult


def format_json(result: LintResult) -> str:
    """Format linting results as JSON.

    Args:
        result: The linting result to format.

    Returns:
        JSON string matching the schema in data-model.md.
    """
    output = {
        "files": [
            {
                "path": str(file_result.path),
                "violations": [
                    {
                        "line": v.line,
                        "column": v.column,
                        "rule_id": v.rule_id,
                        "rule_name": v.rule_name,
                        "message": v.message,
                        "context": v.context,
                    }
                    for v in file_result.violations
                ],
                "error": file_result.error,
            }
            for file_result in result.files
            if file_result.violations or file_result.error
        ],
        "summary": {
            "files_checked": result.files_checked,
            "files_with_violations": result.files_with_violations,
            "files_with_errors": result.files_with_errors,
            "total_violations": result.total_violations,
            "exit_code": result.exit_code,
        },
    }

    return json.dumps(output, indent=2)
