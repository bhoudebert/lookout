"""Scenarios of openspec/specs/personalization."""

from datetime import timedelta

import pytest
from tests.support import NOW, FixedClock, database, enrichment, make_item

from lookout.adapters.store.sqlite import SqliteItemRepository, SqliteSignalRepository
from lookout.application.personalize import Personalize
from lookout.application.triage import Action, ItemNotFoundError, Triage
from lookout.domain.item import Item
from lookout.domain.priority import Priority
from lookout.domain.profile import MAX_BOOST, Signal, SignalKind, features, learn
from lookout.domain.rating import Rating


class World:
    """Items, signals and the use cases on one database."""

    def __init__(self, *, minimum: int = 5, half_life: float = 30.0) -> None:
        db = database()
        self.items = SqliteItemRepository(db)
        self.signals = SqliteSignalRepository(db)
        self.clock = FixedClock()
        self.personalize = Personalize(
            self.items, self.signals, self.clock, half_life_days=half_life, minimum_signals=minimum
        )
        self.triage = Triage(self.items, self.personalize, self.clock)

    def add(self, n: int, *, source: str, channel: str, score: int = 50, tags: tuple[str, ...] = ()) -> Item:
        item = make_item(
            f"https://a.test/{source}-{channel}-{n}",
            title=f"{source} {n}",
            sources=(source,),
            channel=channel,
        )
        item = item.enriched(enrichment(score, tags, channel=channel)).assessed(Priority.P2, "x", ())
        self.items.save(item)
        return item

    def stored(self, item: Item) -> Item:
        found = self.items.get(item.id)
        assert found is not None
        return found


def test_rating_a_source_and_category_down_lowers_later_items_inside_their_band() -> None:
    world = World()
    for n in range(5):
        world.triage.rate(world.add(n, source="noisy", channel="industry").id, Rating.DOWN)
    liked = world.add(10, source="quiet", channel="release")
    noisy = world.add(11, source="noisy", channel="industry")
    world.personalize.rerank()
    assert world.stored(noisy).boost < 0
    assert world.stored(noisy).priority is world.stored(liked).priority is Priority.P2
    ids = [
        i.id
        for i in world.items.search(
            __import__("lookout.application.ports", fromlist=["x"]).InboxQuery()
        ).items
    ]
    assert ids.index(liked.id) < ids.index(noisy.id)


def test_rating_an_author_and_a_channel_down_lowers_later_items_by_them() -> None:
    world = World()
    for n in range(5):
        item = make_item(
            f"https://a.test/n{n}",
            sources=(f"s{n}",),
            author="Spammy Writer",
            channel="Gossip",
            score=50,
        )
        world.items.save(item)
        world.triage.rate(item.id, Rating.DOWN)
    liked = make_item(
        "https://a.test/liked",
        sources=("fresh",),
        author="Good Writer",
        channel="Rust",
        score=50,
    )
    disliked = make_item(
        "https://a.test/disliked",
        sources=("fresh",),
        author="spammy writer",
        channel="Gossip",
        score=50,
    )
    world.items.save(liked)
    world.items.save(disliked)
    world.personalize.rerank()
    assert world.stored(liked).boost == 0
    assert world.stored(disliked).boost < 0
    features = {c.feature for c in world.personalize.explain(disliked.id).contributions}
    assert {"author:spammy writer", "category:Gossip"} <= features


def test_the_articles_own_tags_count_once_with_the_models() -> None:
    item = make_item(feed_tags=("rust", "async"), score=50).enriched(enrichment(50, ("rust", "web")))
    assert [f for f in features(item) if f.startswith("tag:")] == ["tag:rust", "tag:async", "tag:web"]


def test_starring_and_rating_up_teach_the_opposite() -> None:
    world = World()
    for n in range(3):
        world.triage.act(world.add(n, source="gold", channel="release", tags=("python",)).id, Action.STAR)
    for n in range(3, 5):
        world.triage.rate(world.add(n, source="gold", channel="release").id, Rating.UP)
    fresh = world.add(9, source="gold", channel="release", tags=("python",))
    world.personalize.rerank()
    assert world.stored(fresh).boost > 0


def test_nothing_is_learnt_before_the_minimum_number_of_signals() -> None:
    world = World(minimum=5)
    for n in range(4):
        world.triage.rate(world.add(n, source="noisy", channel="industry").id, Rating.DOWN)
    assert world.personalize.profile().weights == {}
    assert world.personalize.rerank() == 0


def test_the_boost_is_bounded_and_never_changes_the_priority() -> None:
    world = World()
    for n in range(40):
        world.triage.act(world.add(n, source="s", channel="c", tags=("a", "b", "c")).id, Action.STAR)
    item = world.add(99, source="s", channel="c", tags=("a", "b", "c"))
    world.personalize.rerank()
    stored = world.stored(item)
    assert stored.boost == MAX_BOOST
    assert stored.priority is Priority.P2


def test_old_signals_count_less() -> None:
    world = World(minimum=1, half_life=10.0)
    old = world.add(1, source="s", channel="c")
    world.triage.act(old.id, Action.STAR)
    fresh_weight = world.personalize.profile().weights["source:s"]
    world.clock.advance(days=10)
    assert world.personalize.profile().weights["source:s"] == pytest.approx(fresh_weight / 2)


def test_opening_counts_once_and_snoozing_teaches_nothing() -> None:
    world = World(minimum=1)
    item = world.add(1, source="s", channel="c")
    world.triage.act(item.id, Action.OPEN)
    world.triage.act(item.id, Action.OPEN)
    world.triage.act(item.id, Action.SNOOZE, until=NOW + timedelta(days=1))
    kinds = [s.kind for s in world.signals.all()]
    assert kinds == [SignalKind.OPEN, SignalKind.SNOOZE]
    assert world.personalize.profile().weights["source:s"] == pytest.approx(1.0)


def test_finishing_reopening_and_unstarring_record_nothing() -> None:
    world = World()
    item = world.add(1, source="s", channel="c")
    world.triage.act(item.id, Action.DONE)
    world.triage.act(item.id, Action.REOPEN)
    world.triage.act(item.id, Action.UNSTAR)
    assert world.signals.all() == ()


def test_explanation_shows_priority_reason_score_and_each_contribution() -> None:
    world = World(minimum=1)
    for n in range(2):
        world.triage.act(world.add(n, source="gold", channel="release", tags=("python",)).id, Action.STAR)
    target = world.add(9, source="gold", channel="release", score=64, tags=("python",))
    world.personalize.rerank()
    explanation = world.personalize.explain(target.id)
    assert (explanation.priority, explanation.priority_reason, explanation.model_score) == (
        Priority.P2,
        "x",
        64,
    )
    assert explanation.boost == world.stored(target).boost > 0
    assert {c.feature for c in explanation.contributions} == {
        "source:gold",
        "category:release",
        "tag:python",
    }
    strengths = [abs(c.points) for c in explanation.contributions]
    assert strengths == sorted(strengths, reverse=True)


def test_explaining_an_unknown_item_is_reported() -> None:
    with pytest.raises(ItemNotFoundError):
        World().personalize.explain("nope")


def test_explanation_of_an_unread_item_has_no_model_score() -> None:
    world = World()
    item = make_item()
    world.items.save(item)
    assert world.personalize.explain(item.id).model_score is None


def test_resetting_forgets_the_profile_and_keeps_the_items() -> None:
    world = World()
    for n in range(5):
        world.triage.rate(world.add(n, source="noisy", channel="industry").id, Rating.DOWN)
    victim = world.add(9, source="noisy", channel="industry")
    world.personalize.rerank()
    assert world.stored(victim).boost < 0
    world.personalize.reset()
    assert world.signals.all() == ()
    assert world.stored(victim).boost == 0
    assert all(i.rating is Rating.NONE for i in world.items.all())
    assert len(world.items.all()) == 6


def test_signals_for_deleted_items_are_ignored() -> None:
    items: dict[str, Item] = {}
    signals = [Signal("gone", SignalKind.STAR, NOW)]
    assert learn(signals, items, NOW, half_life_days=30, minimum=1).weights == {}


def test_features_of_an_unread_item_are_its_sources_and_channel() -> None:
    assert features(make_item(sources=("a", "b"))) == ("source:a", "source:b", "category:Other")
