# Digests of many items

When 140 news items are waiting, you do not want 140 titles: you want a page that says what happened. A **digest**
asks a model to condense a selection into a few dense lines per category, each citing the items it came from, with a
short headline on top.

## Using it

1. In the inbox, narrow what you want with the filters (a category such as `News`, the last day, a priority...).
2. Click **Summarise these N...**. The model reads the selection, most urgent first, up to `digest.max_items` (200 by
   default). It takes a minute or two with a local model; the button says so while it works.
3. Read the page: the headline, then a section per top category, each point with its sources as links. Items no point
   cites are listed apart as **not covered**, so nothing is hidden.
4. **Mark the N cited items done** clears what you have read in one action. The digest stays readable, and **Digest**
   in the menu lists the recent ones. A digest is kept as written: opening it again costs nothing.

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

`digest.context_chars` (40000 by default, about 10 000 tokens) is how much one call may read; a category that
does not fit is written in several parts. Raise it if your model has the room, lower it if it has less. Models that
"think" before answering work: what is between `<think>` tags is dropped.

How to choose the context so that nothing runs on the CPU, how to read Ollama's memory figures and what to do when a
digest seems stuck are in [local models: context, memory and speed](/local-models).
