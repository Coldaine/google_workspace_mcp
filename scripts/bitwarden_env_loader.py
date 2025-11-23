"""Bitwarden Secrets Loader (Python)

Loads secrets defined in `secrets/bitwarden_map.json` using the Bitwarden CLI.
Requires:
  - Bitwarden CLI installed (`bw` in PATH)
  - Unlocked session token exported as BW_SESSION

Outputs shell-compatible `export KEY=value` lines (or `setx` guidance on Windows) to stdout.
Values are never persisted to disk. Intended for local dev or CI bootstrap.
"""

import json
import os
import subprocess
import sys
from typing import Dict, Any

MAP_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "secrets", "bitwarden_map.json")

def load_map() -> Dict[str, Any]:
    try:
        with open(MAP_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: mapping file not found at {MAP_PATH}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in mapping file: {e}", file=sys.stderr)
        sys.exit(2)

def fetch_item(item_id: str) -> Dict[str, Any]:
    try:
        result = subprocess.run(["bw", "get", "item", item_id], capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error fetching Bitwarden item {item_id}: {e.stderr}", file=sys.stderr)
        sys.exit(3)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON for item {item_id}: {e}", file=sys.stderr)
        sys.exit(3)

def extract_field(item: Dict[str, Any], field_name: str) -> str:
    # Try custom fields first
    for field in item.get("fields", []) or []:
        if field.get("name") == field_name:
            return field.get("value", "")
    # Fallbacks: login.username / login.password if sensible
    login = item.get("login") or {}
    if field_name.lower() in {"username", "user", "client_id"} and login.get("username"):
        return login.get("username")
    if field_name.lower() in {"password", "secret", "client_secret"} and login.get("password"):
        return login.get("password")
    return ""

def main():
    if "BW_SESSION" not in os.environ:
        print("Error: BW_SESSION not set. Run 'bw unlock --raw' and export the token first.", file=sys.stderr)
        sys.exit(1)
    mapping = load_map()
    missing = []
    outputs = []
    for env_key, spec in mapping.items():
        item_id = spec.get("item_id")
        field = spec.get("field")
        if not item_id or item_id.startswith("REPLACE-WITH"):
            missing.append(env_key)
            continue
        item = fetch_item(item_id)
        value = extract_field(item, field)
        if not value:
            print(f"Warning: field '{field}' not found for item {item_id} (env {env_key})", file=sys.stderr)
            continue
        # Emit POSIX style export; Windows PowerShell script wraps its own logic
        outputs.append(f"export {env_key}='{value}'")
    for line in outputs:
        print(line)
    if missing:
        print(f"Info: placeholders not set for: {', '.join(missing)}", file=sys.stderr)

if __name__ == "__main__":
    main()
