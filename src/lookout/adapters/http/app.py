"""The HTTP API (openspec: dashboard, triage, scheduling). Thin: every route calls one use case."""

from datetime import datetime, timedelta
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from lookout.adapters.http.schemas import (
    ActionIn,
    ActionOut,
    BulkIn,
    BulkOut,
    ChannelOut,
    ExplanationOut,
    Health,
    ItemDetail,
    ItemOut,
    ItemPage,
    RunOut,
    SeenBelowIn,
    SourceOut,
    SourcePatch,
    TaxonomyOut,
    UndoOut,
)
from lookout.application.ports import InboxQuery
from lookout.application.services import Services
from lookout.application.sources import DisabledInConfigError, UnknownSourceError
from lookout.application.triage import Action, ItemNotFoundError
from lookout.domain.item import InvalidTransitionError
from lookout.domain.priority import Priority
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
        priority: Annotated[list[Literal["P0", "P1", "P2", "P3"]] | None, Query()] = None,
        kind: Annotated[list[str] | None, Query()] = None,
        channel: Annotated[list[str] | None, Query()] = None,
        source: Annotated[list[str] | None, Query()] = None,
        state: Annotated[list[State] | None, Query()] = None,
        starred: bool | None = None,
        text: str = "",
        limit: Annotated[int, Query(ge=1, le=500)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> ItemPage:
        query = InboxQuery(
            priorities=frozenset(Priority[p] for p in priority or []),
            kinds=frozenset(kind or []),
            channels=frozenset(channel or []),
            sources=frozenset(source or []),
            states=frozenset(state) if state else DEFAULT_STATES,
            starred=starred,
            text=text,
            limit=limit,
            offset=offset,
        )
        page = services.inbox.list(query)
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
        before = outcome.before
        return ActionOut(
            item=ItemOut.of(outcome.after),
            undo=UndoOut(state=before.state, snoozed_until=before.snoozed_until, starred=before.starred),
        )

    @app.post("/api/items/{item_id}/restore")
    def restore(item_id: str, body: UndoOut) -> ItemOut:
        try:
            item = services.triage.restore(item_id, body.state, body.snoozed_until, starred=body.starred)
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

    @app.post("/api/items/seen-below")
    def seen_below(body: SeenBelowIn) -> BulkOut:
        return BulkOut(changed=services.triage.mark_seen_below(Priority[body.priority]))

    @app.get("/api/taxonomy")
    def taxonomy() -> TaxonomyOut:
        return TaxonomyOut(
            channels=[ChannelOut(name=c.name, description=c.description) for c in services.channels],
            kinds=list(services.kinds),
        )

    @app.get("/api/sources")
    def sources() -> list[SourceOut]:
        return [SourceOut.of(v) for v in services.sources.list()]

    @app.patch("/api/sources/{name}")
    def patch_source(name: str, body: SourcePatch) -> SourceOut:
        try:
            return SourceOut.of(services.sources.set_enabled(name, enabled=body.enabled))
        except UnknownSourceError:
            raise HTTPException(404, f"no source {name}") from None
        except DisabledInConfigError:
            raise HTTPException(409, f"{name} is disabled in lookout.yaml; enable it there") from None

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
