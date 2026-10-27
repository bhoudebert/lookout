# Local models: context, memory and speed

Lookout talks to any OpenAI-compatible model. This page is for people running them with **Ollama on their own
graphics card**, where the difference between a fast run and a painfully slow one is almost always memory. It is
written from a real case: a digest that ran at 3 tokens per second, and the same digest at 8 once it fitted.

## One server, many projects

Ollama is a single server for everything on your machine: Lookout, your editor, other projects. Its settings are
global. In NixOS that looks like this:

```nix
services.ollama.environmentVariables = {
  OLLAMA_CONTEXT_LENGTH = "65536"; # default context for every model
  OLLAMA_FLASH_ATTENTION = "1";
  OLLAMA_KV_CACHE_TYPE = "q8_0"; # smaller context cache
};
```

If another project needs a long context, leave that alone. Lookout does not need you to change it: a model can carry
its own settings, and those win over the server default.

## What the context costs

The **context** is how many tokens (a token is about four characters) the model can hold at once: the prompt plus the
answer. It is not free. Every token of context takes memory, the **context cache**, in addition to the model's weights:

| Memory         | What                                              | Grows with                 |
| -------------- | ------------------------------------------------- | -------------------------- |
| Weights        | The model itself (llama3.1 8B is about 4.4 GB)    | The model, not the context |
| Context cache  | What the model remembers of the prompt and answer | The context size           |
| Compute buffer | Scratch space for a calculation                   | A little with the context  |

For llama3.1 8B with a `q8_0` cache the context cache is about 68 KiB per token: 0.5 GB at 8k tokens, 1.6 GB at 24k and
**4.4 GB at 64k**. Reading one item needs maybe 2,000 tokens, so a 64k context for it is almost all waste.

## Why it ends up on the CPU

When the memory a model needs is more than the graphics card has **free**, Ollama puts some of the layers on the CPU.
That is called offloading, and it is slow: `ollama ps` shows it as `42%/58% CPU/GPU` instead of `100% GPU`.

The word that matters is _free_. A 16 GB card is not 16 GB for Ollama: the desktop, a browser with hardware
acceleration, a game or another model can hold several gigabytes. In the case this page comes from, a 16 GB card had
only 6.8 GB free because a game was running. llama3.1 at 64k needed 9.1 GB (4.4 weights, 4.35 context cache, 0.36
compute), so 3.3 GB went to the CPU and generation ran at **3.3 tokens per second**. With the context cut and the
memory freed it ran **entirely on the GPU at 8.3 tokens per second**.

## Giving Lookout its own sizes

Lookout reaches Ollama through the OpenAI-compatible API, and that API has no field for "use a context of N". So the
size goes in the model, with a **Modelfile**: a small named copy of a model with other settings. It shares the weights
of the original, so it costs no disk space, and it changes nothing for your other projects.

```
# Modelfile.reader: reads each item (short prompts)
FROM llama3.1:8b
PARAMETER num_ctx 8192
```

```
# Modelfile.digest: writes digests (long prompts)
FROM gemma4:12b
PARAMETER num_ctx 24576
```

```
ollama create lookout-reader -f Modelfile.reader
ollama create gemma4-digest -f Modelfile.digest
```

Then point Lookout at them:

```yaml
llm:
  model: lookout-reader
digest:
  model: gemma4-digest
```

Recreate a model with the same command after you edit its Modelfile. `ollama show gemma4-digest --modelfile` shows what
it carries, and `ollama rm gemma4-digest` removes the copy without touching the original.

## How big a context do you need?

The context must hold the whole prompt plus the answer. If it is smaller, Ollama silently drops the oldest tokens and the
result is wrong without any error. So there is a minimum and a maximum:

- **Minimum, what the task needs.** Reading an item: about 2,000 tokens, so 4k to 8k is plenty. A digest: the prompt is
  at most `digest.context_chars` (40,000 characters by default, about 10,000 tokens) plus up to a few thousand tokens of
  answer, so 16k is the least and 24k is comfortable. If you lower `context_chars`, the context can go down with it.
- **Maximum, what your memory allows.** See the next section.

Pick the smallest context that is comfortably above the minimum. A bigger one buys nothing and costs memory.

## How to find the context that fits

The budget is:

```
free VRAM − weights − compute buffer − about 1 GB of margin = room for the context cache
```

The margin is Ollama's own: its log says _cannot meet free memory target of 1024 MiB_ when it cannot leave a gigabyte
free. To see the real numbers instead of estimating them, load the model and read what Ollama printed:

```
# the memory the model asked for, per device (model, context, compute, in MiB)
journalctl -u ollama --no-pager | grep -A3 "memory breakdown" | tail

# how that compares with what was free
journalctl -u ollama --no-pager | grep "projected to use" | tail -1

# the answer: this should say 100% GPU
ollama ps
```

If the projected use is more than the free memory minus 1,024 MiB, either lower `num_ctx`, free memory (close what uses
the GPU), or take a smaller model. Check what holds your VRAM with `nvidia-smi` (or `nvtop`) before blaming the model.
If you run Ollama with systemd, `journalctl -u ollama -f` is also the way to watch it work: the `print_timing` lines
show tokens generated and tokens per second.

A model that does not fit at all is not a failure, only slow. Half the layers on the CPU is roughly half the speed or
worse.

## A digest that seems stuck

A digest of many items can take a long time, and Ollama's log shows the speed but never the text, so it can look dead.
Check three things:

1. `ollama ps` lists the model: it is loaded. Loading a model that is not yet in memory takes tens of seconds, during
   which nothing is listed.
2. `journalctl -u ollama -f` shows `print_timing` lines with a growing `n_gen`: it is writing.
3. `ss -tnp | grep 11434` shows a connection from `lookout`: the request is open.

The speed tells you how long it takes: 3 tokens per second means about 20 minutes for a 4,000-token answer, 8 means
about 8.

## A model that never stops

Some models "think" before they answer, and Ollama's log counts that thinking as generated tokens. A digest that seems to
run for ever with a fast `tokens per second` is usually this: the log shows thousands of tokens and Lookout shows no
answer. Lookout caps the answer and asks the model not to think (see [digests](/digest)), so it now fails with the reason
instead.

## Stopping a request

Ollama stops generating when the program that asked disconnects. So the clean way to stop a digest is to stop the
Lookout server (Ctrl-C in the terminal running `lookout serve`), and Ollama stops within seconds. Two things that do not
do it:

- `ollama stop <model>` unloads the model only after the running request finishes.
- `systemctl restart ollama` does stop it, but also kills whatever your other projects are running on that server.

Stopping Lookout loses the digest being written, so wait if it is close to done.

## Which model reads best

Reading is the work that runs after every sweep, so speed and a short top of the inbox matter more than polish. We read
the same 1000 items of a real inbox (30 sources, English and French, 574 of them in sources that allow several
categories) with the reader code of Lookout, one model after another, on an RTX 5080 with a 4k to 8k context and
thinking switched off (`reasoning_effort: none`).

|                                             | llama3.1 8B | qwen3 8B | qwen3-vl 8B instruct | gemma4 12B |
| ------------------------------------------- | ----------- | -------- | -------------------- | ---------- |
| Valid answers                               | 96.5%       | 99.6%    | 99.6%                | 96.5%      |
| Items left unread (invalid category twice)  | 35          | 4        | 4                    | 35         |
| Median seconds per item                     | 0.7         | 0.8      | 1.2                  | 1.3        |
| Items per hour                              | 4300        | 3700     | 2250                 | 2500       |
| Same category as the majority of the models | 78%         | 74%      | 86%                  | 86%        |
| Share of items scored 70 or more (P0 or P1) | 25%         | 40%      | 11%                  | 8%         |
| Summary length (characters)                 | 104         | 91       | 166                  | 236        |

What to take from it:

- **qwen3-vl 8B instruct is the default we recommend.** It answers almost always, its scores are spread so the top of the
  inbox stays short, and it reads 300 new items in about 6 minutes. The "vl" part (images) is not used: what matters is
  that it is the instruct (non-thinking) build.
- **llama3.1 8B is the fastest** but files badly across similar categories (a LEGO deal in Cycling) and leaves 3.5% of the
  items unread.
- **qwen3 8B inflates scores**: four items in ten reach P0 or P1, so the top stops meaning anything.
- **gemma4 12B writes the best summaries** and is the strictest on scores, but loses as many items as llama3.1 and
  sometimes stops at the parent category.
- **Not worth it for reading:** qwen3 14B is twice as slow (2.2 s per item) for no clear gain, and thinking switched on
  (`reasoning_effort: medium`) is four times slower (4.6 s per item) without fixing the scores.
- **Asking for several items at once does not help**: requests sent in parallel were no faster (62, 58, 54 and 58 items a
  minute with 1, 2, 4 and 8 at once), because one Ollama server answers one request at a time unless
  `OLLAMA_NUM_PARALLEL` is raised, which also multiplies the memory kept for context.

Caveats: there is no list of right answers, so "same category as the majority" shows consistency, not accuracy, and the
numbers come from one inbox and one GPU. Judge a model on your own sources: [a model per source](#a-model-per-source) lets
you give one source another model and compare.

## A model per source

One model does not read everything equally well: a model strong in English can file French deals badly. A source can
name its own model, served by the same Ollama:

```yaml
llm:
  model: lookout-reader
  reasoning_effort: none # sent with every reading; harmless for models that do not think
sources:
  - name: "Dealabs: Hot"
    type: rss
    url: https://www.dealabs.com/rss/hot
    model: qwen3:8b # reads this source only; empty means llm.model
```

The same field is in the source form of the dashboard (**Model**) and in the Sources table. An item cited by several
sources is read by the model of the first one that names a model. Each model you name takes its own memory when it is
loaded, so name few, and give each the same small context as `llm.model` (a `Modelfile` with `num_ctx 4096`).

## A checklist

- [ ] The server default (`OLLAMA_CONTEXT_LENGTH`) is whatever your other projects need; Lookout does not depend on it.
- [ ] `llm.model` has a small context (4k to 8k), `digest.model` one that fits your free memory (16k to 32k).
- [ ] `ollama ps` shows `100% GPU` for both while they work.
- [ ] Nothing else heavy is using the card while a digest runs (check `nvidia-smi`).
