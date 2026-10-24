"""The ``lookout`` command."""

from importlib.metadata import version as package_version

import typer

app = typer.Typer(
    help="Lookout: a watch tower for the feeds, releases and advisories that matter.", no_args_is_help=True
)


@app.callback()
def root() -> None:
    """Keep ``lookout`` a command group as subcommands are added."""


@app.command()
def version() -> None:
    """Print the installed version."""
    typer.echo(package_version("lookout"))


def main() -> None:
    """Console script entry point."""
    app()
