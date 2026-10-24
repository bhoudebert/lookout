#!/bin/sh
# Start the image the way a user would, and check the API and the dashboard answer. Usage: smoke-image.sh IMAGE
set -eu
image=${1:?usage: smoke-image.sh IMAGE}
dir=$(mktemp -d)
mkdir -p "$dir/config" "$dir/data"
chmod 777 "$dir/data"
printf 'schedule:\n  interval_minutes: 0\n' > "$dir/config/lookout.yaml"

docker run --rm -v "$dir/config:/config:ro" -v "$dir/data:/data" "$image" lookout demo
cid=$(docker run -d -p 127.0.0.1:18899:8899 -v "$dir/config:/config:ro" -v "$dir/data:/data" "$image")
trap 'docker rm -f "$cid" >/dev/null; rm -rf "$dir"' EXIT

for _ in $(seq 1 30); do
  curl -fs http://127.0.0.1:18899/api/health >/dev/null && break
  sleep 1
done
curl -fs http://127.0.0.1:18899/api/health | grep -q '"status":"ok"'
curl -fs http://127.0.0.1:18899/api/items | grep -q '"total":6'
curl -fs http://127.0.0.1:18899/ | grep -q '<div id="root">'
echo "image ok: API, demo data and dashboard answer"
