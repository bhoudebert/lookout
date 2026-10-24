"""Health checks behind ``lookout doctor`` (openspec: cli, "Doctor")."""

from collections.abc import Callable
from typing import Any, cast

import httpx

from lookout.adapters.github.unavailable import REASON
from lookout.adapters.store.sqlite import MIGRATIONS, Database
from lookout.application.ports_sources import SourceError, SourceFetcher
from lookout.application.services import Check
from lookout.bootstrap.config import Config


def run_checks(
    config: Config,
    database: Database,
    llm_http: httpx.Client,
    fetchers: tuple[SourceFetcher, ...],
    github_via: str,
) -> tuple[Check, ...]:
    """Check the database, the model endpoint and every enabled source."""
    checks = [_database(config, database), _llm(config, llm_http)]
    if any(s.type == "github" for s in config.sources):
        checks.append(_github(github_via))
    checks.extend(_source(fetcher.name, fetcher.fetch) for fetcher in fetchers)
    if not fetchers:
        checks.append(Check("sources", ok=False, detail="no source is enabled; declare some in lookout.yaml"))
    return tuple(checks)


def _database(config: Config, database: Database) -> Check:
    version = database.query("PRAGMA user_version")[0][0]
    return Check(
        "database",
        ok=True,
        detail=f"{config.database} at schema version {version}/{len(MIGRATIONS)}",
    )


def _llm(config: Config, http: httpx.Client) -> Check:
    llm = config.llm
    url = llm.base_url.rstrip("/") + "/models"
    headers = {"Authorization": f"Bearer {llm.api_key}"} if llm.api_key else {}
    try:
        response = http.get(url, headers=headers)
        response.raise_for_status()
        models = {str(m.get("id")) for m in cast("list[dict[str, Any]]", response.json().get("data", []))}
    except (httpx.HTTPError, ValueError, AttributeError) as error:
        hint = " Is Ollama running? Start it with `ollama serve`." if "localhost" in llm.base_url else ""
        return Check("llm", ok=False, detail=f"{url}: {error}.{hint}")
    if llm.model not in models and f"{llm.model}:latest" not in models:
        return Check(
            "llm",
            ok=False,
            detail=f"{url} answers but has no model '{llm.model}'. Try `ollama pull {llm.model}`.",
        )
    return Check("llm", ok=True, detail=f"{llm.base_url} serves {llm.model}")


def _source(name: str, fetch: Callable[[], tuple[object, ...]]) -> Check:
    try:
        count = len(fetch())
    except SourceError as error:
        return Check(f"source {name}", ok=False, detail=str(error))
    return Check(f"source {name}", ok=True, detail=f"{count} entries")


def _github(via: str) -> Check:
    if via == "unavailable":
        return Check("github", ok=False, detail=f"{REASON}.")
    return Check("github", ok=True, detail=f"reading through {'your gh login' if via == 'gh' else 'a token'}")
