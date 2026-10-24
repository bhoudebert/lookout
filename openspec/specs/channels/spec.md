# Channels Specification (channels)

## Purpose

File every item in one category (channel), using what the source already says before asking the model. Categories form a
tree such as `Dev > Rust` (ADR 0015).

## Requirements

### Requirement: Channels

The user SHALL be able to declare channels, each with a name and an optional one-line description. A name is a path of
1 to 4 segments of at most 40 characters joined by `>`, such as `Dev > Rust`; declaring a path SHALL create its missing
parents. The channel `Other` SHALL always exist. Names SHALL be unique, ignoring case and spacing around the separator.

#### Scenario: A subcategory

- **WHEN** the user declares `Dev > Rust` and `Dev` does not exist
- **THEN** both exist, and filtering by `Dev` includes the items filed in `Dev > Rust`

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

### Requirement: Facts from the source

The author and the tags an article carries (feed categories) SHALL be stored as facts and shown with the item. The model
SHALL NOT change them; its own tags, which include what the item is (release, tutorial, ...), are kept separately.

### Requirement: Filtering

The inbox SHALL filter by channel, including its subcategories, independently of the other filters, in the API, the
dashboard and the command line.

### Requirement: Existing data

Opening a database made before channels existed SHALL keep every item, with the channel `Other`, no author, and its
former category as a tag. A former kind SHALL also become a tag, and kinds are no longer stored.
