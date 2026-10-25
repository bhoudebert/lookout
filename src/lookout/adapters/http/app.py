"""The HTTP API (openspec: dashboard, triage, scheduling). Thin: every route calls one use case."""

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timedelta
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from lookout.adapters.http.schemas import (
    ActionIn,
    ActionOut,
    BulkIn,
    BulkOut,
    ChannelIn,
    ChannelMove,
    ChannelOut,
    ChannelPatch,
    ExplanationOut,
    Health,
    ItemDetail,
    ItemFilter,
    ItemOut,
    ItemPage,
    RatingIn,
    RefileOut,
    RestoreIn,
    RunOut,
    SeenBelowIn,
    SourceBody,
    SourceCreate,
    SourceOut,
    SourcePatch,
    SourceTypeOut,
    SweepIn,
    SweepOut,
    TaxonomyOut,
    UndoEntry,
    UndoOut,
)
from lookout.application.ports import InboxQuery, Order
from lookout.application.registry import DuplicateError, InUseError, InvalidError, NotFoundError
from lookout.application.services import Services
from lookout.application.triage import Action, ItemNotFoundError, TooManyItemsError, Undo
from lookout.domain.channel import Channel
from lookout.domain.item import InvalidTransitionError
from lookout.domain.priority import Priority
from lookout.domain.rating import Rating
from lookout.domain.source import SourceDef
from lookout.domain.state import State

DEFAULT_STATES = frozenset({State.NEW, State.SEEN})


def create_app(services: Services, static_dir: Path | None = None) -> FastAPI:
    """Build the API around the application. ``static_dir`` is the built dashboard, served at ``/``."""
    app = FastAPI(
        title="Lookout",
        version=package_version("lookout"),
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    @app.get("/api/health")
    def health() -> Health:
        return Health(status="ok", version=package_version("lookout"))

    @app.get("/api/items")
    def list_items(
        selection: Annotated[ItemFilter, Query()],
        order: Order = Order.PRIORITY,
        limit: Annotated[int, Query(ge=1, le=500)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> ItemPage:
        page = services.inbox.list(
            replace(_query(selection, services.clock.now()), order=order, limit=limit, offset=offset)
        )
        return ItemPage(items=[ItemOut.of(i) for i in page.items], total=page.total)

    @app.get("/api/items/{item_id}")
    def get_item(item_id: str) -> ItemDetail:
        item = services.items.get(item_id)
        if item is None:
            raise HTTPException(404, f"no item {item_id}")
        return ItemDetail(
            item=ItemOut.of(item),
            body=item.body,
            explanation=ExplanationOut.of(services.personalize.explain(item_id)),
        )

    @app.post("/api/items/{item_id}/actions")
    def act(item_id: str, body: ActionIn) -> ActionOut:
        until = _wake(services.clock.now(), body) if body.action is Action.SNOOZE else None
        try:
            outcome = services.triage.act(item_id, body.action, until=until)
        except ItemNotFoundError:
            raise HTTPException(404, f"no item {item_id}") from None
        except InvalidTransitionError as error:
            raise HTTPException(409, str(error)) from error
        return ActionOut(item=ItemOut.of(outcome.after), undo=UndoOut.of(outcome.before))

    @app.post("/api/items/{item_id}/rating")
    def rate(item_id: str, body: RatingIn) -> ActionOut:
        try:
            outcome = services.triage.rate(item_id, Rating(body.rating))
        except ItemNotFoundError:
            raise HTTPException(404, f"no item {item_id}") from None
        return ActionOut(item=ItemOut.of(outcome.after), undo=UndoOut.of(outcome.before))

    @app.post("/api/items/{item_id}/restore")
    def restore(item_id: str, body: UndoOut) -> ItemOut:
        try:
            item = services.triage.restore(_undo(item_id, body))
        except ItemNotFoundError:
            raise HTTPException(404, f"no item {item_id}") from None
        return ItemOut.of(item)

    @app.post("/api/items/bulk")
    def bulk(body: BulkIn) -> BulkOut:
        until = _wake(services.clock.now(), body) if body.action is Action.SNOOZE else None
        try:
            outcomes = services.triage.act_many(tuple(body.ids), body.action, until=until)
        except ItemNotFoundError as error:
            raise HTTPException(404, f"no item {error}") from error
        except InvalidTransitionError as error:
            raise HTTPException(409, str(error)) from error
        return BulkOut(changed=len(outcomes))

    @app.post("/api/items/sweep")
    def sweep(body: SweepIn) -> SweepOut:
        now = services.clock.now()
        until = _wake(now, body) if body.action is Action.SNOOZE else None
        try:
            result = services.triage.sweep(
                _query(body.filter, now), body.action, until=until, dry_run=body.dry_run
            )
        except TooManyItemsError as error:
            raise HTTPException(422, str(error)) from error
        except InvalidTransitionError as error:
            raise HTTPException(409, str(error)) from error
        return SweepOut(
            matched=result.matched,
            changed=len(result.outcomes),
            sample=[ItemOut.of(i) for i in result.sample],
            undo=[UndoEntry(id=o.before.id, **UndoOut.of(o.before).model_dump()) for o in result.outcomes],
        )

    @app.post("/api/items/restore-many")
    def restore_many(body: RestoreIn) -> BulkOut:
        try:
            services.triage.restore_many(tuple(_undo(entry.id, entry) for entry in body.entries))
        except ItemNotFoundError as error:
            raise HTTPException(404, f"no item {error}") from error
        return BulkOut(changed=len(body.entries))

    @app.post("/api/items/seen-below")
    def seen_below(body: SeenBelowIn) -> BulkOut:
        return BulkOut(changed=services.triage.mark_seen_below(Priority[body.priority]))

    @app.get("/api/taxonomy")
    def taxonomy(selection: Annotated[ItemFilter, Query()]) -> TaxonomyOut:
        """The categories, each with how many items the same filters would list in it (the category aside)."""
        everywhere = replace(_query(selection, services.clock.now()), channels=frozenset())
        counts = services.items.count_by_channel(everywhere)
        feeders = services.registry.sources()
        return TaxonomyOut(
            channels=[
                ChannelOut(
                    name=c.name,
                    description=c.description,
                    items=counts.get(c.name, 0),
                    sources=[s.name for s in feeders if c.name.lower() in (n.lower() for n in s.channels)],
                )
                for c in services.registry.channels()
            ],
        )

    @app.post("/api/refile")
    def refile(dry_run: bool = False) -> RefileOut:
        report = services.refile.run(dry_run=dry_run)
        return RefileOut(filed=report.filed, queued=report.queued)

    @app.get("/api/source-types")
    def source_types() -> list[SourceTypeOut]:
        return [SourceTypeOut.of(info) for info in services.source_types]

    @app.get("/api/sources")
    def sources() -> list[SourceOut]:
        return [SourceOut.of(v) for v in services.sources.list()]

    @app.post("/api/sources", status_code=201)
    def add_source(body: SourceCreate) -> SourceOut:
        stored = _guard(lambda: services.registry.add_source(_definition(body.name, body)))
        return SourceOut.of(services.sources.view(stored))

    @app.put("/api/sources/{name}")
    def change_source(name: str, body: SourceBody) -> SourceOut:
        stored = _guard(lambda: services.registry.update_source(_definition(name, body)))
        return SourceOut.of(services.sources.view(stored))

    @app.patch("/api/sources/{name}")
    def patch_source(name: str, body: SourcePatch) -> SourceOut:
        stored = _guard(lambda: services.registry.set_enabled(name, enabled=body.enabled))
        return SourceOut.of(services.sources.view(stored))

    @app.delete("/api/sources/{name}", status_code=204)
    def delete_source(name: str) -> None:
        _guard(lambda: services.registry.remove_source(name))

    @app.post("/api/channels", status_code=201)
    def add_channel(body: ChannelIn) -> ChannelOut:
        stored = _guard(lambda: services.registry.add_channel(Channel(body.name, body.description)))
        return ChannelOut(name=stored.name, description=stored.description)

    @app.patch("/api/channels/{name}")
    def change_channel(name: str, body: ChannelPatch) -> ChannelOut:
        stored = _guard(lambda: services.registry.update_channel(name, body.description))
        return ChannelOut(name=stored.name, description=stored.description)

    @app.post("/api/channels/{name}/move")
    def move_channel(name: str, body: ChannelMove) -> ChannelOut:
        stored = _guard(lambda: services.registry.move_channel(name, body.parent))
        return ChannelOut(name=stored.name, description=stored.description)

    @app.delete("/api/channels/{name}", status_code=204)
    def delete_channel(name: str) -> None:
        _guard(lambda: services.registry.remove_channel(name))

    @app.get("/api/run")
    def run_status() -> RunOut:
        return RunOut.of(services.runs.status())

    @app.post("/api/run", status_code=202)
    def run_now() -> RunOut:
        status, started = services.runs.start()
        return RunOut.of(status, started=started)

    @app.delete("/api/profile", status_code=204)
    def forget() -> None:
        services.personalize.reset()

    if static_dir is not None and static_dir.is_dir():
        _serve_dashboard(app, static_dir)
    return app


def _definition(name: str, body: SourceBody) -> SourceDef:
    return SourceDef(
        name=name,
        type=body.type,
        settings=body.settings,
        channels=tuple(body.channels),
        keywords=tuple(body.keywords),
        enabled=body.enabled,
    )


def _guard[T](change: Callable[[], T]) -> T:
    """Run a change to sources or channels, turning what it refuses into the right HTTP answer."""
    try:
        return change()
    except NotFoundError as error:
        raise HTTPException(404, f"no such source or channel: {error}") from None
    except (DuplicateError, InUseError) as error:
        raise HTTPException(409, str(error)) from None
    except InvalidError as error:
        raise HTTPException(422, str(error)) from None


def _undo(item_id: str, body: UndoOut) -> Undo:
    return Undo(
        item_id,
        body.state,
        body.snoozed_until,
        body.starred,
        Rating(body.rating),
        body.rated_at,
    )


def _query(selection: ItemFilter, now: datetime) -> InboxQuery:
    """The inbox query a filter stands for; the age filters are counted back from now."""
    return InboxQuery(
        priorities=frozenset(Priority[p] for p in selection.priority),
        channels=frozenset(selection.channel),
        sources=frozenset(selection.source),
        states=frozenset(selection.state) if selection.state else DEFAULT_STATES,
        starred=selection.starred,
        text=selection.text,
        published_before=None
        if selection.older_than_days is None
        else now - timedelta(days=selection.older_than_days),
        published_after=None
        if selection.newer_than_days is None
        else now - timedelta(days=selection.newer_than_days),
    )


def _wake(now: datetime, body: ActionIn) -> datetime:
    if body.until is None:
        return now + timedelta(hours=body.hours)
    return body.until if body.until.tzinfo else body.until.replace(tzinfo=now.tzinfo)


def _serve_dashboard(app: FastAPI, root: Path) -> None:
    assets = root / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def dashboard(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(404)
        target = (root / path).resolve()
        if path and target.is_file() and root.resolve() in target.parents:
            return FileResponse(target)
        return FileResponse(root / "index.html")
