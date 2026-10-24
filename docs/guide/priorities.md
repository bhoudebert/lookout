# How priority is decided

Priority is computed by code, in this order, and the **model can raise a priority but never lower it below a rule**.

## 1. Rule floors

Facts, not opinions. They apply when an item carries a structured advisory that affects something in your declared stack:

| Fact                  | At least |
| --------------------- | -------- |
| Known to be exploited | P0       |
| Critical severity     | P0       |
| High severity         | P1       |

An advisory for a package you do not use gets no floor, except one raised on a [GitHub repository you watch](/sources), which counts as affecting you. Severity and the exploited flag come from the sources (OSV, GitHub, CISA), never from the model.

## 2. The model's score

Above the floor, the model's score from 0 to 100 is banded:

| Score    | Priority |
| -------- | -------- |
| 90 – 100 | P0       |
| 70 – 89  | P1       |
| 40 – 69  | P2       |
| 0 – 39   | P3       |

Change the bands with `thresholds` in [the configuration](/configuration).

## 3. The reason

Every item keeps how it got its priority: `rule: critical advisory CVE-2026-1234 affects django, which you use`, or `model score 85: You write Python.`. The dashboard shows it; `lookout explain <id>` prints it.

## Changing your stack

Edit the stack, then run `lookout reassess`. Priorities of stored items are recomputed without calling the model.

## What your actions change

Your actions never change the priority. They only reorder items **inside** a priority. See [personalization](/personalization).
