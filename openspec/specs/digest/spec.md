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
- **THEN** the attempt fails with "nothing matches this selection" and no digest is kept

#### Scenario: The model fails

- **WHEN** the model is unreachable, or gives no valid answer twice
- **THEN** the attempt fails with the reason and no digest is kept

### Requirement: Written in the background

A digest SHALL be written in the background, one at a time: asking for another while one is being written SHALL show
the running one instead of starting a second. The server SHALL keep, in memory only, the digest being written and how
the last attempts ended (done, failed with the reason, cancelled) until the user dismisses them: what part is being
written (a category, then the headline, out of how many), about how many tokens the model has written, and when it
started. A restart forgets them. The user SHALL be able to cancel a digest being written, which SHALL stop asking the
model for more at once, and to dismiss a finished attempt.

#### Scenario: Leave and come back

- **WHEN** the user asks for a digest and then opens another page, or reloads
- **THEN** the digest keeps being written, and the Digest page and the header show it as being written

#### Scenario: Cancel

- **WHEN** the user cancels a digest being written
- **THEN** the model is no longer waited for, no digest is kept, and the attempt shows as cancelled

#### Scenario: Failure stays visible

- **WHEN** the model fails while a digest is written
- **THEN** the attempt stays listed with the reason until the user dismisses it

### Requirement: A model cannot run away

The answer of the model SHALL be read as it is written and bounded: a section is cut at `digest.max_answer_tokens` and
the headline at a smaller bound, and reaching the bound SHALL fail the attempt saying so, and, when the model wrote no
answer at all, saying that it kept thinking. The model SHALL be asked not to think when the server supports it
(`digest.reasoning_effort`, empty to not ask) and for at most about one point per three items. An answer wrapped in a
code fence or a sentence SHALL still be read.

#### Scenario: A thinking model

- **WHEN** the model spends all its tokens thinking and writes no answer
- **THEN** the attempt fails at the bound, explaining that the model kept thinking

### Requirement: Cited items are real

A point SHALL cite only items that were given to the model. A citation of a number outside them SHALL be dropped, and a
point left with no valid citation SHALL be dropped. Items no point cites SHALL be listed apart as not covered.

The model SHALL be asked to cite every item it is given, merging only items about the same story, and an item it leaves
out SHALL be asked about once more, apart from the others. Items still left out after that SHALL be listed as not
covered.

#### Scenario: The model skips items

- **WHEN** the model writes points citing 5 of 13 items
- **THEN** it is asked again about the other 8, and the digest covers all 13 if it answers

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

The dashboard SHALL offer "Summarise these" on the current selection of the inbox, saying that the digest is written
in the background and will appear under Digest, without waiting on that page. The Digest page SHALL list the digests
being written or lately finished above the digests kept (part being written, tokens, time, Cancel or Dismiss, the
reason of a failure, a link to a finished one), and the header SHALL show a digest being written or just finished on
every page. A digest SHALL have its own page (headline, sections, points with their sources as links, items not
covered), and the user SHALL be able to mark the cited items done in one action and delete a digest. Source links
SHALL only be web addresses.

#### Scenario: Summarise, read, clear

- **WHEN** the user summarises the inbox, opens the finished digest and chooses to mark the cited items done
- **THEN** those items leave the inbox and the digest stays readable

#### Scenario: Seeing that something is happening

- **WHEN** a digest is being written
- **THEN** the Digest page shows it with the part being written and the tokens so far, without the user asking again
