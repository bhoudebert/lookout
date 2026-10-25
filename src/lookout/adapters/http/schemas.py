"""The JSON shapes of the API. The frontend's TypeScript types are generated from these."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from lookout.application.personalize import Explanation
from lookout.application.runs import RunStatus
from lookout.application.source_types import SourceTypeInfo
from lookout.application.sources import SourceView
from lookout.application.triage import Action
from lookout.domain.item import Item
from lookout.domain.state import State

EXCERPT_CHARS = 600


class ItemOut(BaseModel):
    """An item as the inbox lists it."""

    id: str
    url: str
    title: str
    summary: str | None
    excerpt: str
    published_at: datetime
    sources: list[str]
    channel: str
    author: str
    feed_tags: list[str]
    tags: list[str]
    priority: str
    priority_label: str
    priority_reason: str
    action_needed: bool
    state: State
    snoozed_until: datetime | None
    starred: bool
    stack_matches: list[str]
    enrichment_failed: bool
    unread: bool = Field(description="True while the model has not read the item and has not failed on it.")
    score: int | None
    boost: int
    rating: int = Field(description="1 thumbs up, -1 thumbs down, 0 none.")

    @classmethod
    def of(cls, item: Item) -> "ItemOut":
        reading = item.enrichment
        return cls(
            id=item.id,
            url=item.url,
            title=item.title,
            summary=reading.summary if reading else None,
            excerpt=item.body[:EXCERPT_CHARS],
            published_at=item.published_at,
            sources=list(item.sources),
            channel=item.channel,
            author=item.author,
            feed_tags=list(item.feed_tags),
            tags=list(reading.tags) if reading else [],
            priority=item.priority.name,
            priority_label=item.priority.label,
            priority_reason=item.priority_reason,
            action_needed=reading.action_needed if reading else False,
            state=item.state,
            snoozed_until=item.snoozed_until,
            starred=item.starred,
            stack_matches=list(item.stack_matches),
            enrichment_failed=item.enrichment_failed,
            unread=reading is None and not item.enrichment_failed,
            score=reading.score if reading else None,
            boost=item.boost,
            rating=int(item.rating),
        )


class ItemPage(BaseModel):
    """A page of the inbox."""

    items: list[ItemOut]
    total: int


class ContributionOut(BaseModel):
    """One line of "why this rank"."""

    feature: str
    points: int


class ExplanationOut(BaseModel):
    """Why an item ranks where it does."""

    priority: str
    priority_reason: str
    model_score: int | None
    boost: int
    contributions: list[ContributionOut]

    @classmethod
    def of(cls, why: Explanation) -> "ExplanationOut":
        return cls(
            priority=why.priority.name,
            priority_reason=why.priority_reason,
            model_score=why.model_score,
            boost=why.boost,
            contributions=[ContributionOut(feature=c.feature, points=c.points) for c in why.contributions],
        )


class ItemDetail(BaseModel):
    """One item with its full text and the rank explanation."""

    item: ItemOut
    body: str
    explanation: ExplanationOut


class Wake(BaseModel):
    """When a snoozed item comes back."""

    hours: float = Field(default=24.0, gt=0, description="Snooze duration, used by `snooze` without `until`.")
    until: datetime | None = None


class ActionIn(Wake):
    """Do something to an item."""

    action: Action


class UndoOut(BaseModel):
    """What to send back to put an item as it was."""

    state: State
    snoozed_until: datetime | None
    starred: bool
    rating: int = Field(default=0, ge=-1, le=1)
    rated_at: datetime | None = None

    @classmethod
    def of(cls, item: Item) -> "UndoOut":
        return cls(
            state=item.state,
            snoozed_until=item.snoozed_until,
            starred=item.starred,
            rating=int(item.rating),
            rated_at=item.rated_at,
        )


class RatingIn(BaseModel):
    """Thumbs up (1), thumbs down (-1); the rating the item already has clears it."""

    rating: int = Field(ge=-1, le=1)


class ActionOut(BaseModel):
    """The item after an action, and how to undo it."""

    item: ItemOut
    undo: UndoOut


class BulkIn(ActionIn):
    """The same action on several items."""

    ids: list[str] = Field(min_length=1)


PriorityName = Literal["P0", "P1", "P2", "P3"]


class ItemFilter(BaseModel):
    """What to select, as the inbox filters do. Empty means no filter; states default to new and seen."""

    priority: list[PriorityName] = Field(default_factory=list[PriorityName])
    channel: list[str] = Field(default_factory=list[str])
    source: list[str] = Field(default_factory=list[str])
    state: list[State] = Field(default_factory=list[State])
    starred: bool | None = None
    text: str = ""
    older_than_days: int | None = Field(default=None, ge=0)
    newer_than_days: int | None = Field(default=None, ge=0)


class SweepIn(Wake):
    """An action or a rating on everything a filter matches; ``dry_run`` only says what would change."""

    action: Action | None = None
    rating: int | None = Field(default=None, ge=-1, le=1, description="Set this rating instead of acting.")
    filter: ItemFilter = Field(default_factory=ItemFilter)
    dry_run: bool = False

    @model_validator(mode="after")
    def _one_of_action_or_rating(self) -> "SweepIn":
        if (self.action is None) == (self.rating is None):
            msg = "give an action or a rating, not both and not neither"
            raise ValueError(msg)
        return self


class BulkRatingIn(BaseModel):
    """Give these items one rating (set, never toggled): 1, -1, or 0 to clear."""

    ids: list[str] = Field(min_length=1)
    rating: int = Field(ge=-1, le=1)


class BulkRatingOut(BaseModel):
    """How many items were rated, and how to put them back."""

    changed: int
    undo: list["UndoEntry"]


class UndoEntry(UndoOut):
    """One item's undo, with its id."""

    id: str


class SweepOut(BaseModel):
    """What a sweep matched, a sample of it, and how to undo what it changed."""

    matched: int
    changed: int
    sample: list[ItemOut]
    undo: list[UndoEntry]


class RestoreIn(BaseModel):
    """Put several items back as they were."""

    entries: list[UndoEntry] = Field(min_length=1)


class BulkOut(BaseModel):
    """How many items changed."""

    changed: int


class SeenBelowIn(BaseModel):
    """Mark new items less urgent than this as seen."""

    priority: str = Field(pattern="^P[0-3]$")


class SourceOut(BaseModel):
    """A source, its settings and how its last run went."""

    name: str
    type: str
    enabled: bool
    channels: list[str]
    keywords: list[str]
    settings: dict[str, Any]
    last_run: datetime | None
    last_error: str | None
    items_seen: int

    @classmethod
    def of(cls, view: SourceView) -> "SourceOut":
        return cls(
            name=view.name,
            type=view.type,
            enabled=view.enabled,
            channels=list(view.channels),
            keywords=list(view.keywords),
            settings=view.settings,
            last_run=view.last_run,
            last_error=view.last_error,
            items_seen=view.items_seen,
        )


class SourceBody(BaseModel):
    """Everything about a source except its name."""

    type: str
    settings: dict[str, Any] = Field(default_factory=dict[str, Any])
    channels: list[str] = Field(default_factory=list[str], description="Empty means every channel.")
    keywords: list[str] = Field(default_factory=list[str])
    enabled: bool = True


class SourceCreate(SourceBody):
    """A new source."""

    name: str


class FieldOut(BaseModel):
    """One setting a type of source takes."""

    name: str
    label: str
    kind: str = Field(description="text, list (one entry per line), bool or number")
    required: bool
    default: Any = None
    help: str


class SourceTypeOut(BaseModel):
    """A type of source and the form it needs."""

    name: str
    label: str
    description: str
    fields: list[FieldOut]

    @classmethod
    def of(cls, info: SourceTypeInfo) -> "SourceTypeOut":
        return cls(
            name=info.name,
            label=info.label,
            description=info.description,
            fields=[
                FieldOut(
                    name=f.name,
                    label=f.label,
                    kind=f.kind,
                    required=f.required,
                    default=f.default,
                    help=f.help,
                )
                for f in info.fields
            ],
        )


class ChannelIn(BaseModel):
    """A new channel."""

    name: str
    description: str = ""


class ChannelPatch(BaseModel):
    """A new description for a channel."""

    description: str


class ChannelMove(BaseModel):
    """Where to move a category: inside this one, or to the top level when empty."""

    parent: str = ""


class SourcePatch(BaseModel):
    """Switch a source on or off."""

    enabled: bool


class SourceRunOut(BaseModel):
    """What a source did in the last run."""

    name: str
    fetched: int
    new: int
    error: str | None
    skipped: bool


class RunOut(BaseModel):
    """The current or last run."""

    running: bool
    started: bool = Field(description="True when this request started the run.")
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
    sources: list[SourceRunOut]
    enriched: int
    failed: int
    waiting: int

    @classmethod
    def of(cls, status: RunStatus, *, started: bool = False) -> "RunOut":
        report = status.report
        return cls(
            running=status.running,
            started=started,
            started_at=status.started_at,
            finished_at=status.finished_at,
            error=status.error,
            sources=[
                SourceRunOut(name=s.name, fetched=s.fetched, new=s.new, error=s.error, skipped=s.skipped)
                for s in (report.ingest.sources if report else ())
            ],
            enriched=report.enrich.enriched if report else 0,
            failed=report.enrich.failed if report else 0,
            waiting=report.enrich.waiting if report else 0,
        )


class Health(BaseModel):
    """Liveness."""

    status: str
    version: str


class ChannelOut(BaseModel):
    """A category (channel) the user follows, with how much it holds and who feeds it."""

    name: str
    description: str
    items: int = 0
    sources: list[str] = Field(default_factory=list[str], description="The sources that name this category.")


class RefileOut(BaseModel):
    """What filing existing items again did."""

    filed: int = Field(description="Items filed in a category by rule.")
    queued: int = Field(description="Items the model will read again at the next run.")


class TaxonomyOut(BaseModel):
    """The categories items can be filed in."""

    channels: list[ChannelOut]
