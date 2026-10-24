# Categories Specification (categories)

## Purpose

Make categories (channels, ADR 0012) and kinds first-class in the dashboard, and let existing items follow them
(ADR 0014).

## Requirements

### Requirement: A page of categories

The dashboard SHALL have a page, next to the inbox and the sources, where the user defines categories. It SHALL list
each category with its description, the number of items it holds and the sources that name it (or say that any source
may feed it), and SHALL offer one-click suggestions for categories that do not exist yet.

#### Scenario: A new install

- **WHEN** only `Other` exists
- **THEN** the page suggests starting categories, and adding one takes a single click

### Requirement: Kinds

The user SHALL be able to add and delete kinds of item. A kind SHALL be stored lower-case with single spaces, 1 to 40
characters; names are unique; `other` SHALL always exist and SHALL NOT be deleted. The model SHALL choose among the kinds
as they are when it is asked, ignoring case, and items keep a kind that is later deleted.

### Requirement: Filing existing items again

The user SHALL be able to file existing items again. An item whose sources allow exactly one category SHALL be filed
there by rule. An item in `Other` that the model has read and whose sources allow several categories SHALL be queued to
be read again at the next run. Nothing else changes, and the daily model budget still applies.

#### Scenario: Categories added after items exist

- **WHEN** the user adds categories and files items again
- **THEN** the items the model read are queued, and after the next run each is in the category the model chose

### Requirement: Other is a last resort

The prompt SHALL tell the model to choose the most specific category that fits and to pick `Other` only when none fits,
and SHALL describe `Other` that way unless the user wrote a description for it.

### Requirement: Say when nothing is filed

While every item shown in the inbox is in `Other`, the inbox SHALL say so and link to the categories page.

### Requirement: Existing databases

A database made before editable kinds SHALL get its kinds from the configuration file once, even if its sources and
channels were seeded earlier.
