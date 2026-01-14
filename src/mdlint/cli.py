import dataclasses
import sys
from pathlib import Path
from typing import Literal, get_args, get_origin

import rich_click as click
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.syntax import Syntax

from mdlint import __version__
from mdlint.config import apply_cli_overrides, load_config
from mdlint.linter import Linter, LintResult, discover_files
from mdlint.output.json import format_json
from mdlint.output.terminal import print_results
from mdlint.rules import RULE_REGISTRY

# Width for rule documentation output and help output
RULE_DOC_WIDTH = 120
HELP_CONFIG_WIDTH = 120
RULE_DOC_INDENT = 2

CONTEXT_SETTINGS = {
    "help_option_names": ["-h", "--help"],
}


@click.group(context_settings=CONTEXT_SETTINGS)
@click.rich_config(
    help_config=click.RichHelpConfiguration(text_markup="markdown", width=HELP_CONFIG_WIDTH)
)
@click.version_option(version=__version__, prog_name="mdlint")
def cli() -> None:
    """mdlint - A Python Markdown linter."""


@cli.command()
@click.rich_config(
    help_config=click.RichHelpConfiguration(
        option_groups={
            "mdlint check": [
                {
                    "name": "Rule selection",
                    "options": ["--select", "--ignore", "--extend-select", "--extend-ignore"],
                },
                {
                    "name": "File selection",
                    "options": ["--exclude", "--extend-exclude", "--no-ignore"],
                },
                {
                    "name": "Output options",
                    "options": ["--format", "--verbose", "--show-files", "--show-context"],
                },
            ],
        },
        width=HELP_CONFIG_WIDTH,
    )
)
@click.argument("paths", nargs=-1, type=click.Path())
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["terminal", "json"]),
    default="terminal",
    help="Output format.",
)
@click.option(
    "--config",
    "-c",
    "config_path",
    type=str,
    default=None,
    help="Path to config file or inline TOML (e.g., MD003.style='atx').",
)
@click.option(
    "--select",
    "-s",
    multiple=True,
    help="Rules to run. Replaces any select list in config (repeatable).",
)
@click.option(
    "--ignore",
    "-i",
    multiple=True,
    help="Rules to skip. Replaces any ignore list in config (repeatable).",
)
@click.option(
    "--extend-select",
    "-S",
    multiple=True,
    help="Rules to add on top of the select list (repeatable).",
)
@click.option(
    "--extend-ignore",
    "-I",
    multiple=True,
    help="Rules to add on top of the ignore list (repeatable).",
)
@click.option(
    "--exclude",
    multiple=True,
    help="Exclude files/directories from analysis. Replaces config exclude list (repeatable).",
)
@click.option(
    "--extend-exclude",
    multiple=True,
    help="Exclude files/directories on top of the config exclude list (repeatable).",
)
@click.option(
    "--no-ignore",
    is_flag=True,
    default=False,
    help="Disable .gitignore pattern matching.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Show files being processed.",
)
@click.option(
    "--show-files",
    is_flag=True,
    default=False,
    help="List files that would be linted and exit.",
)
@click.option(
    "--show-context",
    is_flag=True,
    default=False,
    help="Show surrounding lines for each violation.",
)
def check(
    paths: tuple[str, ...],
    output_format: str,
    config_path: str | None,
    select: tuple[str, ...],
    ignore: tuple[str, ...],
    extend_select: tuple[str, ...],
    extend_ignore: tuple[str, ...],
    exclude: tuple[str, ...],
    extend_exclude: tuple[str, ...],
    no_ignore: bool,
    verbose: bool,
    show_files: bool,
    show_context: bool,
) -> None:
    """Lint Markdown files for style violations.

    PATHS can be files or directories. Use '-' for stdin. If no paths provided, lints current
    directory.
    """
    # Validate CLI options - check for unknown rules
    all_rules = set(select) | set(ignore) | set(extend_select) | set(extend_ignore)
    unknown = all_rules - set(RULE_REGISTRY.keys())
    if unknown:
        rules = ", ".join(sorted(unknown))
        click.echo(f"Error: Unknown rule(s): {rules}", err=True)
        sys.exit(2)

    # Load configuration
    config = load_config(config_path=config_path)
    config = apply_cli_overrides(
        config,
        select=select,
        ignore=ignore,
        extend_select=extend_select,
        extend_ignore=extend_ignore,
    )

    if verbose and config.source:
        click.secho(f"Using config: {config.source}", dim=True, err=True)

    linter = Linter(rule_configs=config.rules, enabled_rules=config.enabled_rules)
    if verbose:
        click.secho(
            f"Linting with these rules enabled: {', '.join(sorted(config.enabled_rules))}",
            dim=True,
            err=True,
        )

    # Handle stdin
    if len(paths) == 1 and paths[0] == "-":
        content = sys.stdin.read()
        file_result = linter.lint_stdin(content)
        result = LintResult(files=[file_result])
    else:
        # Default to current directory if no paths
        if not paths:
            paths = (".",)

        path_list = [Path(p) for p in paths]
        for path in path_list:
            if not path.exists():
                click.echo(f"Error: no such file or directory: {path}", err=True)
                sys.exit(2)

        if exclude:
            exclude_list: list[str] | None = list(exclude)
        else:
            exclude_list = config.exclude.copy() or None
        if extend_exclude:
            if exclude_list is None:
                exclude_list = []
            exclude_list.extend(extend_exclude)

        if show_files:
            files = discover_files(
                path_list, respect_gitignore=not no_ignore, exclude_patterns=exclude_list
            )
            for file in files:
                click.echo(file)
            sys.exit(0)

        if verbose:
            click.secho(f"Scanning {len(path_list)} path(s)...", dim=True, err=True)

        result = linter.lint_paths(
            path_list, respect_gitignore=not no_ignore, exclude_patterns=exclude_list
        )

        if verbose:
            click.secho(f"Found {result.files_checked} file(s)", dim=True, err=True)

    # Output results
    if output_format == "json":
        click.echo(format_json(result))
    else:
        print_results(result, show_context=show_context)

    sys.exit(result.exit_code)


@cli.command()
@click.argument("rule_id", required=False)
@click.option(
    "--show-examples",
    "-e",
    is_flag=True,
    default=False,
    help="Show valid/invalid examples for the rule.",
)
def rule(rule_id: str | None, show_examples: bool) -> None:
    """Display rule documentation.

    If RULE_ID is provided, shows detailed documentation for that rule.
    Otherwise, lists all available rules.
    """
    console = Console(width=RULE_DOC_WIDTH)

    if rule_id is None:
        # List all rules
        console.print("[bold]Available rules:[/bold]\n")
        for rid, rule_class in sorted(RULE_REGISTRY.items()):
            console.print(f"  [yellow]{rid}[/yellow]  {rule_class.name:20}  {rule_class.summary}")
        raise SystemExit(0)  # ty doesn't recognize sys.exit(0) as terminating function

    # Resolve partial rule ID to full ID
    # Accept numeric input (e.g., "1" -> "MD001") or MD-prefixed (case-insensitive)
    if rule_id.isdigit():
        resolved_id = f"MD{int(rule_id):03d}"
    elif rule_id.upper().startswith("MD"):
        resolved_id = rule_id.upper()
    else:
        click.echo(f"Error: Invalid rule ID '{rule_id}'", err=True)
        sys.exit(2)

    if resolved_id not in RULE_REGISTRY:
        click.echo(f"Error: Unknown rule '{resolved_id}'", err=True)
        sys.exit(2)

    rule_class = RULE_REGISTRY[resolved_id]
    console.print(f"[bold yellow]{rule_class.id}[/bold yellow]: {rule_class.name}\n")
    console.print(f"  {rule_class.summary}\n")

    if rule_class.description:
        console.print(Padding("[bold]What it does:[/bold]", (0, 0, 0, RULE_DOC_INDENT)))
        console.print(Padding(Markdown(rule_class.description), (0, 0, 1, RULE_DOC_INDENT)))

    if rule_class.rationale:
        console.print(Padding("[bold]Why is this bad?[/bold]", (0, 0, 0, RULE_DOC_INDENT)))
        console.print(Padding(Markdown(rule_class.rationale), (0, 0, 1, RULE_DOC_INDENT)))

    config_class = rule_class.config_class
    config_fields = list(dataclasses.fields(config_class))
    if config_fields:
        console.print("  [bold]Configuration:[/bold]")
        for f in config_fields:
            default = f.default if f.default is not dataclasses.MISSING else None
            # Extract metadata
            metadata = f.metadata if f.metadata else {}
            description = metadata.get("description", "")
            option_descriptions = metadata.get("option_descriptions", {})
            # Extract options from Literal types
            field_type = f.type
            options = None
            if get_origin(field_type) is Literal:
                options = get_args(field_type)
            if description:
                console.print(Padding(f"[cyan]{f.name}[/cyan]: {description}", (0, 0, 0, 4)))
            else:
                console.print(Padding(f"[cyan]{f.name}[/cyan]", (0, 0, 0, 4)))
            console.print(Padding(f"default: {default}", (0, 0, 0, 6)))
            if options:
                if option_descriptions:
                    console.print("      options:")
                    # Calculate max width for alignment
                    max_width = max(len(str(o)) for o in options)
                    for opt in options:
                        opt_desc = option_descriptions.get(opt, "")
                        console.print(f"        {opt:<{max_width}} - {opt_desc}")
                else:
                    options_str = " | ".join(str(o) for o in options)
                    console.print(f"      options: {options_str}")
        console.print()

    if not show_examples:
        return

    panel_width = RULE_DOC_WIDTH - RULE_DOC_INDENT
    panels = []

    if rule_class.example_invalid:
        syntax = Syntax(rule_class.example_invalid.rstrip(), "markdown", theme="ansi_dark")
        panel = Panel(
            syntax,
            title="[red]Invalid[/red]",
            title_align="left",
            border_style="red",
            width=panel_width,
        )
        panels.append(panel)

    if rule_class.example_valid:
        syntax = Syntax(rule_class.example_valid.rstrip(), "markdown", theme="ansi_dark")
        panel = Panel(
            syntax,
            title="[green]Valid[/green]",
            title_align="left",
            border_style="green",
            width=panel_width,
        )
        panels.append(panel)

    if panels:
        console.print(Padding(Group(*panels), (0, 0, 0, RULE_DOC_INDENT)))


if __name__ == "__main__":
    cli()
