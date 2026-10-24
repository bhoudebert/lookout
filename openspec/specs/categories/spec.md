# Categories Specification (categories)

## Purpose

Make categories (channels, one tree, ADR 0015) first-class in the dashboard, and let existing items follow them
(ADR 0014).

## Requirements

### Requirement: A page of categories

The dashboard SHALL have a page, next to the inbox and the sources, where the user defines categories. It SHALL list
each category with its description, the number of items it holds and the sources that name it (or say that any source
may feed it), and SHALL offer one-click suggestions for categories that do not exist yet.

#### Scenario: A new install

- **WHEN** only `Other` exists
- **THEN** the page suggests starting categories, and adding one takes a single click

### Requirement: A tree beside the inbox

The inbox SHALL show the categories as a tree with the number of items in each, beside the list; choosing one filters by
it and its subcategories, and `All` clears it.

#### Scenario: Browsing a branch

- **WHEN** the user chooses `Dev`
- **THEN** the list holds the items of `Dev` and of `Dev > Rust`, and the URL records the choice

### Requirement: Subcategories

The user SHALL be able to add a category inside another. A category that has subcategories or is named by a source SHALL
NOT be deleted, and neither SHALL `Other`.

### Requirement: Filing existing items again

The user SHALL be able to file existing items again. An item whose sources allow exactly one category SHALL be filed
there by rule. An item the model has read that sits in `Other`, or in a category that now has subcategories, and whose
sources allow several categories SHALL be queued to be read again at the next run. Nothing else changes, and the daily
model budget still applies.

#### Scenario: Offer after creating

- **WHEN** the user creates a category
- **THEN** the page says how many items would be filed again and offers to do it now or not; nothing changes until the
  user accepts

#### Scenario: Categories added after items exist

- **WHEN** the user adds categories and files items again
- **THEN** the items the model read are queued, and after the next run each is in the category the model chose

### Requirement: Other is a last resort

The prompt SHALL tell the model to choose the most specific category that fits and to pick `Other` only when none fits,
and SHALL describe `Other` that way unless the user wrote a description for it.

### Requirement: Say when nothing is filed

While every item shown in the inbox is in `Other`, the inbox SHALL say so and link to the categories page.
