# Getting started

You need Python 3.13, Node 24 and [Ollama](https://ollama.com). With [Nix](https://nixos.org) one command gives you all of it.

## Install

```sh
git clone https://github.com/bhoudebert/lookout
cd lookout
nix develop          # Python, uv, Node, just, gh, Chromium for the tests
just setup           # dependencies and git hooks
```

With [direnv](https://direnv.net), run `direnv allow` once and the shell loads by itself whenever you enter the folder (add [nix-direnv](https://github.com/nix-community/nix-direnv) to cache it).

Without Nix, install Python 3.13, [uv](https://docs.astral.sh/uv/), Node 24 and [just](https://just.systems), then run `just setup`.

## Ready-made commands

From the repository, without entering the shell:

```sh
nix run .#dev                   # demo data, builds the dashboard, serves it
nix run .#lookout -- inbox      # any lookout command
nix run .#doctor                # check the setup
nix run .#quality               # the full gate
```

Inside the shell (or with direnv) `lookout` is on your PATH.

## Try it with demo data

```sh
cp lookout.example.yaml lookout.yaml
lookout demo           # six believable items
npm run --prefix frontend build
lookout serve          # http://127.0.0.1:8899
```

Open the address in a browser. The first item is a critical advisory on Django, which `lookout.example.yaml` declares in your stack: it is **P0**, and opening it shows the rule that put it there.

## Use it for real

1. Start Ollama and pull a model: `ollama pull llama3.1` is enough to start. For better readings, see [which model reads best](/local-models#which-model-reads-best).
2. Edit `lookout.yaml`: list your [sources](/sources), your stack and a sentence about your interests. See [configuration](/configuration).
3. Check everything: `lookout doctor`. It tells you what to fix, for example to start Ollama.
4. Fetch and read: `lookout run`, or press **Run now** in the dashboard.
5. Keep it fresh: `lookout serve` runs on the schedule you set. See [running](/running).

## Next

- [How Lookout thinks](/concepts): items, priorities, states.
- [The dashboard](/dashboard): shortcuts and bulk actions.
