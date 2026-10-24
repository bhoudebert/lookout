# Self-hosting

Lookout is one process and one SQLite file, so it fits a laptop, a home server or a small VPS. There is **no login**: keep it on `127.0.0.1`, or put a proxy that authenticates in front of it.

## Docker

```sh
mkdir -p config && cp lookout.example.yaml config/lookout.yaml   # edit: sources, stack, interests
docker compose -f deploy/docker-compose.yml up -d
docker compose -f deploy/docker-compose.yml exec lookout lookout doctor
```

Open `http://127.0.0.1:8899`. The image is `ghcr.io/bhoudebert/lookout`, published with each release as `latest` and by version. It runs as an unprivileged user, keeps its data in the `/data` volume, reads `/config/lookout.yaml`, and reports its health to Docker.

Ollama on the host is reached as `http://host.docker.internal:11434/v1`, so put that in `llm.base_url` (the compose file adds the host mapping). Secrets go in the environment, not in the file:

```sh
LOOKOUT_LLM_API_KEY=...      # if your endpoint needs a key
LOOKOUT_GITHUB_TOKEN=...     # GitHub sources, since `gh` is not in the image
```

To build the image yourself: `docker build -t lookout .`

## NixOS

```nix
{
  inputs.lookout.url = "github:bhoudebert/lookout";

  # in your system configuration
  imports = [ inputs.lookout.nixosModules.lookout ];
  services.lookout = {
    enable = true;
    configFile = ./lookout.yaml;                    # copied to the store: no secrets in it
    environmentFile = "/run/secrets/lookout.env";   # LOOKOUT_LLM_API_KEY=... and so on
  };
}
```

The module runs the published image, keeps the data in `/var/lib/lookout`, listens on `127.0.0.1:8899`, and installs a `lookout` command that runs inside the container (`lookout doctor`, `lookout inbox`, ...). Set `image` to a version tag to choose when updates happen.

## Backups

Everything is in the SQLite file (`/data/lookout.db` in the container). Copy it while Lookout runs, or export the items: `lookout export > backup.jsonl`.

## Updating

Pull the new image and restart. Schema changes are applied on start, one transaction per step, with a copy of the file written first (`lookout.db.bak-vN`).
