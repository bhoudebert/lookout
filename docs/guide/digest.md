# Digests of many items

When 140 news items are waiting, you do not want 140 titles: you want a page that says what happened. A **digest**
asks a model to condense a selection into a few dense lines per category, each citing the items it came from, with a
short headline on top.

## Using it

1. In the inbox, narrow what you want with the filters (a category such as `News`, the last day, a priority...).
2. Click **Summarise these N...**. The digest is written **in the background**: you can use the rest of Lookout, even
   reload. It says the digest will appear under **Digest**. The model reads the selection, most urgent first, up to
   `digest.max_items` (200 by default), and only one digest is written at a time.
3. Follow it on the **Digest** page, where a **Writing** row shows the part being written (a category, then the
   headline), about how many tokens the model has written, and since when, with a **Cancel** button. The header also
   says "Digest: writing..." on every page, and "ready" when it is done. A failure stays in that row with its reason
   until you dismiss it. These rows live in the server's memory: restarting `lookout serve` forgets a digest that was
   being written.
   The rows also say how many items the digest is made of and **which days they were published** ("40 items published
   20 Oct – 24 Oct 2026"), as soon as the selection is read.
4. Read the page: the headline, then a section per top category, each point with its sources as links. The points group items by
   theme or region, so 140 items become a few dozen lines, not 140. Every item is
   meant to be covered: the model is told to cite them all and merge only the same story, and an item it leaves out is
   asked about once more. Any that is still missing is listed apart as **not covered**, so nothing is hidden.
5. **Mark the N cited items done** clears what you have read in one action. The digest stays readable, and **Digest**
   in the menu lists the recent ones, each with when it was written, how many items it covers and the days they
   were published (digests kept before this was recorded show no dates). Choose how the list is sorted: when it was
   written, newest item, or size. A digest is kept as written: opening it again costs nothing.

It works from what Lookout already holds for each item: the title, the model's own summary of it, and the start of
the feed text. It does **not** open the articles, so a feed that only gives a title (Hacker News, for example) gives
the digest little to condense.

## A bigger model for it

Reading one item is a small, frequent job; a digest is one big call. You can give it its own model:

```yaml
llm:
  model: llama3.1 # reads each item
digest:
  model: gemma4-digest # writes digests
```

`digest.base_url` defaults to `llm.base_url`. The digest model must have room for the whole selection, about 16 000
tokens at the default `context_chars`. With Ollama, do not raise the context of the whole server for that: every model
then reserves the memory, and a model that no longer fits your graphics card runs on the CPU at a fraction of the speed.
Make a copy of the model that has the context only for digests (24 576 tokens is comfortable):

```
# Modelfile
FROM gemma4:12b
PARAMETER num_ctx 24576
```

```
ollama create gemma4-digest -f Modelfile
```

A category is written in calls of at most `digest.items_per_call` items (40 by default); when it takes several calls the
model merges their points by theme, so a big category stays dense.

`digest.context_chars` (40000 by default, about 10 000 tokens) is how much one call may read; a category that
does not fit is written in several parts. Raise it if your model has the room, lower it if it has less. Models that
"think" before answering are a trap, see below.

## Models that think

Some models (gemma4, qwen3, deepseek-r1, gpt-oss...) reason at length before they answer. For a digest that is wasted
time, and a model can think for ever: in the case this page comes from, gemma4 wrote 18 000 tokens of reasoning and no
answer. Lookout protects you in three ways:

- it asks the model **not to think** (`digest.reasoning_effort`, `none` by default; set it to `low` or `medium` for a
  model that wants a level, or to an empty value to send nothing, for a server that refuses the field);
- it **bounds the answer**: `digest.max_answer_tokens` (6144 by default) for a section, and a few hundred for the
  headline. A model that reaches the bound fails the digest with the reason, and when it wrote no answer at all the
  message says it kept thinking;
- it asks for at most about one point per three items, so the answer stays short.

It does not use the model's "JSON mode" for a digest: a thinking model puts its reasoning in the JSON there. An answer
in a code fence or after a sentence is read all the same.

How to choose the context so that nothing runs on the CPU, how to read Ollama's memory figures and what to do when a
digest seems stuck are in [local models: context, memory and speed](/local-models).
