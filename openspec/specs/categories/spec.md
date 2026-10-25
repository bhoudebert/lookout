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

### Requirement: Counts that match the list

The number beside each category SHALL be the number of items the list would show in it (and under it) with the filters
in force, the category aside: the view (inbox by default; done or expired items are not counted in the
inbox), priority, source, star, text and age. `All` SHALL equal the total of the list without a category.

#### Scenario: A category and its list

- **WHEN** a category holds 3 items in the inbox, 1 done and 1 expired
- **THEN** the tree says 3, clicking it lists 3, and in the expired view it says 1

### Requirement: Subcategories

The user SHALL be able to add a category inside another. A category that has subcategories or is named by a source SHALL
NOT be deleted, and neither SHALL `Other`.

### Requirement: Moving a category

The user SHALL be able to move a category, with its subcategories, inside another category or to the top level. The items
filed in it and the sources that name it SHALL follow. A move onto an existing category, inside itself, of `Other`, or
that makes a path deeper than four levels SHALL be refused and change nothing. Every category SHALL have its parents
stored: opening a database that holds a path without its parent SHALL create the parent, and the dashboard SHALL show
only categories the server has.

#### Scenario: Reorganising

- **WHEN** the user moves `Languages` inside `Dev`
- **THEN** `Languages > Rust` becomes `Dev > Languages > Rust`, its items and its sources with it

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
