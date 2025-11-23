#!/usr/bin/env bash
# Bitwarden secrets loader (POSIX shell)
# Usage: source ./scripts/load-secrets.sh

set -euo pipefail
MAP_PATH="${MAP_PATH:-$(dirname "$0")/../secrets/bitwarden_map.json}"

if [[ -z "${BW_SESSION:-}" ]]; then
  echo "BW_SESSION not set. Run: export BW_SESSION=\"$(bw unlock --raw)\"" >&2
  exit 1
fi

if [[ ! -f "$MAP_PATH" ]]; then
  echo "Mapping file not found: $MAP_PATH" >&2
  exit 2
fi

python "$(dirname "$0")/bitwarden_env_loader.py" | while read -r line; do
  if [[ "$line" == export* ]]; then
    eval "$line"
    var_name=$(echo "$line" | cut -d' ' -f2 | cut -d'=' -f1)
    echo "Set $var_name"
  fi
done

echo "Secrets loaded into current shell session."
