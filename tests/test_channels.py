"""Scenarios of openspec/specs/channels."""

import httpx
import pytest
from tests.cli_support import FIXTURES
from tests.support import FakeFetcher, FixedClock, ScriptedEnricher, database, enrichment, make_item, raw

from lookout.adapters.sources.rss import RssFetcher
from lookout.adapters.store.sqlite import (
    SqliteItemRepository,
    SqliteSourceStatusRepository,
    SqliteUsageRepository,
)
from lookout.application.enrich import Enrich
from lookout.application.ingest import Ingest
from lookout.application.ports_sources import EnrichmentError
from lookout.domain.channel import OTHER, Channel, ChannelCatalogue, UnknownChannelError
from lookout.domain.policy import PriorityPolicy
from lookout.domain.stack import Stack

AI, RUST = Channel("AI", "Models and tools"), Channel("Rust")


def catalogue(**routes: tuple[str, ...]) -> ChannelCatalogue:
    return ChannelCatalogue((AI, RUST), routes)


# --- the catalogue ----------------------------------------------------------------------------------------


def test_other_always_exists_and_is_never_duplicated() -> None:
    assert [c.name for c in ChannelCatalogue((AI,)).channels] == ["AI", OTHER]
    assert [c.name for c in ChannelCatalogue((AI, Channel("other"))).channels] == ["AI", "other"]
    assert [c.name for c in ChannelCatalogue().channels] == [OTHER]


def test_a_source_listing_one_channel_files_its_items_there() -> None:
    cat = catalogue(**{"rust-blog": ("Rust",)})
    assert cat.allowed(("rust-blog",)) == (RUST,)
    assert cat.initial(("rust-blog",)) == "Rust"


def test_a_source_listing_several_lets_the_model_choose_among_them() -> None:
    cat = catalogue(**{"mixed": ("ai", "RUST")})
    assert cat.allowed(("mixed",)) == (AI, RUST)
    assert cat.initial(("mixed",)) == OTHER


def test_a_source_listing_none_may_feed_every_channel() -> None:
    cat = catalogue()
    assert [c.name for c in cat.allowed(("anything",))] == ["AI", "Rust", OTHER]
    assert cat.initial(("anything",)) == OTHER


def test_one_source_without_channels_opens_everything_for_a_shared_item() -> None:
    cat = catalogue(**{"rust-blog": ("Rust",)})
    assert len(cat.allowed(("rust-blog", "general"))) == 3
    assert cat.allowed(("rust-blog", "rust-blog")) == (RUST,)


def test_a_source_feeding_an_undeclared_channel_is_refused_naming_it() -> None:
    with pytest.raises(UnknownChannelError, match="source 'x' feeds the channel 'Gardening'"):
        catalogue(x=("Gardening",))


# --- ingestion: facts from the source ----------------------------------------------------------------------


def ingest_world(cat: ChannelCatalogue) -> tuple[Ingest, SqliteItemRepository]:
    db = database()
    items = SqliteItemRepository(db)
    ingest = Ingest(
        items,
        SqliteSourceStatusRepository(db),
        FixedClock(),
        PriorityPolicy(),
        Stack(),
        catalogue=lambda: cat,
    )
    return ingest, items


def test_a_single_channel_source_files_items_before_any_model_call() -> None:
    ingest, items = ingest_world(catalogue(**{"rust-blog": ("Rust",)}))
    ingest.run((FakeFetcher("rust-blog", (raw(source="rust-blog"),)),))
    (item,) = items.all()
    assert item.channel == "Rust"
    assert item.enrichment is None


def test_the_author_and_the_articles_own_tags_are_kept_as_facts() -> None:
    ingest, items = ingest_world(catalogue())
    entry = raw(source="blog")
    entry = type(entry)(
        entry.source,
        entry.url,
        entry.title,
        entry.body,
        entry.published_at,
        None,
        "  Jane <b>Doe</b> ",
        (" Rust ", "rust", "", "Async"),
    )
    ingest.run((FakeFetcher("blog", (entry,)),))
    (item,) = items.all()
    assert (item.author, item.feed_tags) == ("Jane Doe", ("rust", "async"))


def test_the_articles_tags_are_capped() -> None:
    ingest, items = ingest_world(catalogue())
    entry = raw(source="blog")
    many = tuple(f"tag{n}" for n in range(30))
    entry = type(entry)(entry.source, entry.url, entry.title, entry.body, entry.published_at, None, "", many)
    ingest.run((FakeFetcher("blog", (entry,)),))
    assert len(items.all()[0].feed_tags) == 8


# --- enrichment: the model chooses within what the source allows -------------------------------------------


class Choosing(ScriptedEnricher):
    """Records the channels it was offered and answers the one asked for."""

    def __init__(self, answer: str) -> None:
        super().__init__()
        self.answer = answer
        self.offered: list[tuple[str, ...]] = []

    def enrich(self, item, channels, examples=()):  # type: ignore[no-untyped-def]
        self.offered.append(tuple(c.name for c in channels))
        return enrichment(60, channel=self.answer)


def enrich_world(cat: ChannelCatalogue, enricher: ScriptedEnricher) -> tuple[Enrich, SqliteItemRepository]:
    db = database()
    items = SqliteItemRepository(db)
    runner = Enrich(
        items,
        enricher,
        SqliteUsageRepository(db),
        FixedClock(),
        PriorityPolicy(),
        daily_limit=10,
        catalogue=lambda: cat,
    )
    return runner, items


def test_the_model_is_offered_only_what_the_source_allows_and_its_choice_files_the_item() -> None:
    enricher = Choosing("Rust")
    runner, items = enrich_world(catalogue(mixed=("AI", "Rust")), enricher)
    items.save(make_item(sources=("mixed",)))
    runner.run()
    assert enricher.offered == [("AI", "Rust")]
    assert items.all()[0].channel == "Rust"
    assert items.all()[0].enrichment is not None


def test_an_item_the_model_failed_on_keeps_the_channel_its_source_gave() -> None:
    enricher = ScriptedEnricher({"A post": EnrichmentError("no")})
    runner, items = enrich_world(catalogue(**{"rust-blog": ("Rust",)}), enricher)
    items.save(make_item(sources=("rust-blog",), channel="Rust"))
    runner.run()
    assert items.all()[0].channel == "Rust"


# --- the feed adapter -------------------------------------------------------------------------------------


def serve(name: str) -> httpx.Client:
    content = (FIXTURES / name).read_bytes()
    return httpx.Client(transport=httpx.MockTransport(lambda _r: httpx.Response(200, content=content)))


def test_rss_carries_the_author_and_the_category_tags() -> None:
    rust, plain = RssFetcher("blog", "https://x/feed", serve("feed-meta.rss")).fetch()
    assert (rust.author, rust.tags) == ("Ferris Crab", ("Rust", "Release"))
    assert (plain.author, plain.tags) == ("", ())


def test_atom_carries_the_author_and_the_term() -> None:
    (entry,) = RssFetcher("blog", "https://x/feed", serve("feed-meta.atom")).fetch()
    assert (entry.author, entry.tags) == ("Atom Author", ("python",))
