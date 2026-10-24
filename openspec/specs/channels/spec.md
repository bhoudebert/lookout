# Channels and Kinds Specification (channels)

## Purpose

File every item by topic (channel) and by type (kind), using what the source already says before asking the model.

## Requirements

### Requirement: Channels

The user SHALL be able to declare channels, each with a name and an optional one-line description. The channel `Other`
SHALL always exist. Channel names SHALL be unique, ignoring case.

### Requirement: Channels of a source

A source SHALL list the channels it may feed; an empty list means every channel. An item SHALL be filed in the channel
of its source when the source lists exactly one, without asking the model. Otherwise the model SHALL choose among the
source's channels (every channel when it lists none), and its answer SHALL be validated against that set.

#### Scenario: A single-channel source

- **WHEN** the source "rust-blog" lists only the channel "Rust"
- **THEN** its items are in "Rust" before any model call, and stay there whatever the model says

#### Scenario: The model chooses

- **WHEN** a general source lists no channel and the model answers "AI" for an item
- **THEN** the item is in "AI"; an answer that is not a declared channel is refused like any invalid answer

### Requirement: Kinds

The user SHALL be able to edit the list of kinds. The model SHALL choose exactly one kind per item from that list, and an
answer outside it SHALL be refused. An item the model has not read has no kind.

### Requirement: Facts from the source

The author and the tags an article carries (feed categories) SHALL be stored as facts and shown with the item. The model
SHALL NOT change them; its own tags are kept separately.

### Requirement: Filtering

The inbox SHALL filter by channel and by kind independently of each other and of the other filters, in the API, the
dashboard and the command line.

### Requirement: Existing data

Opening a database made before channels existed SHALL keep every item, with the channel `Other`, no author, and its
former category as its kind.
