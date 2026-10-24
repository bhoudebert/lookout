"""The ``lookout`` command (openspec: cli). A thin adapter: every command calls one use case."""

from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Annotated, NoReturn

import typer

from lookout.adapters.store.codec import encode
from lookout.application.errors import ConfigError
from lookout.application.ports import InboxQuery
from lookout.application.services import Services
from lookout.application.triage import Action, ItemNotFoundError
from lookout.domain.item import InvalidTransitionError, Item
from lookout.domain.priority import Priority
from lookout.domain.state import State

Opener = Callable[[Path], Services]
DEFAULT_CONFIG = Path("lookout.yaml")


@dataclass
class _Context:
    open_services: Opener
    config: Path


def create_app(open_services: Opener) -> typer.Typer:
    """Build the command group around a function that opens the application from a config file."""
    app = typer.Typer(
        help="Lookout: a watch tower for the feeds, releases and advisories that matter.",
        no_args_is_help=True,
    )

    @app.callback(no_args_is_help=True)
    def root(
        ctx: typer.Context,
        config: Annotated[
            Path, typer.Option("--config", "-c", envvar="LOOKOUT_CONFIG", help="Path of lookout.yaml.")
        ] = DEFAULT_CONFIG,
    ) -> None:
        """Keep ``lookout`` a command group and remember which configuration to use."""
        ctx.obj = _Context(open_services, config)

    @app.command()
    def version() -> None:
        """Print the installed version."""
        typer.echo(package_version("lookout"))

    @app.command()
    def run(ctx: typer.Context) -> None:
        """Fetch every source, then have the model read the new items."""
        with _open(ctx) as services:
            report = services.run()
        for source in report.ingest.sources:
            if source.skipped:
                typer.echo(f"{source.name}: backing off after an error ({source.error})")
            elif source.error:
                typer.echo(f"{source.name}: FAILED {source.error}")
            else:
                typer.echo(f"{source.name}: {source.fetched} entries, {source.new} new")
        enrich = report.enrich
        typer.echo(f"read {enrich.enriched}, failed {enrich.failed}, waiting for budget {enrich.waiting}")

    @app.command()
    def inbox(
        ctx: typer.Context,
        priority: Annotated[
            list[str] | None, typer.Option("--priority", "-p", help="P0 to P3, repeatable.")
        ] = None,
        category: Annotated[list[str] | None, typer.Option("--category")] = None,
        source: Annotated[list[str] | None, typer.Option("--source")] = None,
        state: Annotated[list[State] | None, typer.Option("--state", help="Default: new and seen.")] = None,
        starred: Annotated[bool, typer.Option("--starred", help="Only starred items.")] = False,
        text: Annotated[str, typer.Option("--text")] = "",
        limit: Annotated[int, typer.Option("--limit")] = 30,
    ) -> None:
        """List items, most urgent first."""
        query = InboxQuery(
            priorities=frozenset(_priority(p) for p in priority or []),
            categories=frozenset(category or []),
            sources=frozenset(source or []),
            states=frozenset(state) if state else frozenset({State.NEW, State.SEEN}),
            starred=True if starred else None,
            text=text,
            limit=limit,
        )
        with _open(ctx) as services:
            page = services.inbox.list(query)
        for item in page.items:
            typer.echo(_line(item))
        typer.echo(f"{len(page.items)} of {page.total}")

    @app.command()
    def act(
        ctx: typer.Context,
        item_id: Annotated[str, typer.Argument(help="Item id, as shown by `inbox`.")],
        action: Annotated[Action, typer.Argument()],
        hours: Annotated[float, typer.Option("--hours", help="Snooze duration.")] = 24.0,
        until: Annotated[
            str | None, typer.Option("--until", help="Snooze until an ISO date and time.")
        ] = None,
    ) -> None:
        """Open, finish, dismiss, snooze or star an item."""
        with _open(ctx) as services:
            wake = _wake(services.clock.now(), hours, until) if action is Action.SNOOZE else None
            try:
                outcome = services.triage.act(item_id, action, until=wake)
            except ItemNotFoundError:
                _die(f"no item {item_id}")
            except InvalidTransitionError as error:
                _die(str(error))
        typer.echo(_line(outcome.after))

    @app.command()
    def doctor(ctx: typer.Context) -> None:
        """Check the database, the model endpoint and every source."""
        with _open(ctx) as services:
            checks = services.doctor()
        for check in checks:
            typer.echo(f"{'ok  ' if check.ok else 'FAIL'} {check.name}: {check.detail}")
        if not all(c.ok for c in checks):
            raise typer.Exit(1)

    @app.command()
    def demo(ctx: typer.Context) -> None:
        """Add demo items to try the dashboard."""
        with _open(ctx) as services:
            typer.echo(f"added {services.seed_demo()} demo items")

    @app.command()
    def reassess(ctx: typer.Context) -> None:
        """Recompute priorities after changing the stack or the thresholds (no model call)."""
        with _open(ctx) as services:
            typer.echo(f"{services.reassess.run()} items changed")

    @app.command()
    def export(ctx: typer.Context) -> None:
        """Print every item as JSON lines."""
        with _open(ctx) as services:
            for item in services.items.all():
                typer.echo(encode(item))

    return app


@contextmanager
def _open(ctx: typer.Context) -> Generator[Services]:
    """Open the application for one command, always close it, turn configuration errors into exit 1."""
    context: _Context = ctx.obj
    try:
        services = context.open_services(context.config)
    except ConfigError as error:
        _die(str(error))
    try:
        yield services
    finally:
        services.close()


def _die(message: str) -> NoReturn:
    typer.echo(message, err=True)
    raise typer.Exit(1)


def _priority(text: str) -> Priority:
    try:
        return Priority[text.upper()]
    except KeyError:
        _die(f"unknown priority '{text}'; use P0, P1, P2 or P3")


def _wake(now: datetime, hours: float, until: str | None) -> datetime:
    if until is None:
        return now + timedelta(hours=hours)
    try:
        moment = datetime.fromisoformat(until)
    except ValueError:
        _die(f"cannot read '{until}' as a date and time (try 2026-10-25T09:00:00+00:00)")
    return moment if moment.tzinfo else moment.replace(tzinfo=now.tzinfo)


def _line(item: Item) -> str:
    category = item.enrichment.category if item.enrichment else "unread"
    star = "*" if item.starred else "-"
    where = f"{', '.join(item.sources)}, {category}"
    return f"{item.priority.name} {star} {item.id} [{item.state.value}] {item.title} ({where})"
