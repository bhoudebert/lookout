# Digest

A very dense summary of many items, for news: the model condenses a selection into a few cited lines per category.

## Requirements

### Requirement: Condense a selection

The user SHALL be able to ask for a digest of the items a filter selects: the most urgent first, up to a configured
maximum. The model SHALL write, for each top category of the selection, short points that merge items about the same
story, each citing the items it was written from, then a headline of two or three sentences on what matters most.
Category sections SHALL be ordered as their first item is, with Other last. A category too big for the model's context
SHALL be written in several parts. The text of items SHALL be treated as data, never as instructions.

#### Scenario: Many items become a few lines

- **WHEN** the user asks for a digest of 140 items
- **THEN** the digest has a headline, a section per top category, and points that cite the items they come from

#### Scenario: Nothing to condense

- **WHEN** the selection matches no item
- **THEN** the user is told there is nothing to condense and no digest is kept

#### Scenario: The model fails

- **WHEN** the model is unreachable, or gives no valid answer twice
- **THEN** the user is told the model could not write the digest and no digest is kept

### Requirement: Cited items are real

A point SHALL cite only items that were given to the model. A citation of a number outside them SHALL be dropped, and a
point left with no valid citation SHALL be dropped. Items no point cites SHALL be listed apart as not covered.

#### Scenario: The model invents a source

- **WHEN** the model cites item 99 among 5
- **THEN** that citation is ignored

### Requirement: Digests are kept

A digest SHALL be stored with its selection in words, so it can be read again without the model. The user SHALL be able
to list the recent digests, open one and delete one. Items a digest cites that no longer exist SHALL be left out of it.

#### Scenario: Read it again

- **WHEN** the user opens a digest made yesterday
- **THEN** it shows the same text, with the current state of each cited item

### Requirement: A model of its own

The digest SHALL use the model, address and settings of the `digest` block of the configuration, falling back to the
`llm` block for what is empty, so a bigger model with a longer context can be used for it alone.

#### Scenario: A bigger model for digests

- **WHEN** the configuration sets `digest.model` to another model than `llm.model`
- **THEN** reading items still uses `llm.model` and digests use `digest.model`

### Requirement: Dashboard

The dashboard SHALL offer "Summarise these" on the current selection of the inbox, show the digest on its own page
(headline, sections, points with their sources as links, items not covered), list the recent digests, and let the user
mark the cited items done in one action, and delete a digest. Source links SHALL only be web addresses.

#### Scenario: Summarise, read, clear

- **WHEN** the user summarises the inbox, reads the digest and chooses to mark the cited items done
- **THEN** those items leave the inbox and the digest stays readable
