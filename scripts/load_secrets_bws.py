import json
import os
import subprocess
import sys

MAP_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "secrets", "bws_map.json")

def main():
    if not os.path.exists(MAP_PATH):
        print(f"Error: {MAP_PATH} not found", file=sys.stderr)
        sys.exit(1)

    with open(MAP_PATH, 'r') as f:
        mapping = json.load(f)

    for env_key, secret_id in mapping.items():
        try:
            result = subprocess.run(
                ["bws", "secret", "get", secret_id],
                capture_output=True,
                text=True,
                check=True
            )
            data = json.loads(result.stdout)
            value = data.get("value")
            if value:
                # Print commands to set env vars
                print(f"export {env_key}='{value}'")
        except subprocess.CalledProcessError as e:
            print(f"# Error fetching {env_key}: {e.stderr}", file=sys.stderr)

if __name__ == "__main__":
    main()
