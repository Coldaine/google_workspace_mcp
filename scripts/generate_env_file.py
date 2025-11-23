import json
import os
import subprocess
import sys

MAP_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "secrets", "bws_map.json")
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

def main():
    if not os.path.exists(MAP_PATH):
        print(f"Error: {MAP_PATH} not found", file=sys.stderr)
        sys.exit(1)

    with open(MAP_PATH, 'r') as f:
        mapping = json.load(f)

    env_content = []
    
    # Read existing .env if it exists to preserve other values
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, 'r') as f:
            for line in f:
                if line.strip() and not any(line.startswith(k + "=") for k in mapping.keys()):
                    env_content.append(line.strip())

    print("Fetching secrets from Bitwarden...")
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
                env_content.append(f"{env_key}={value}")
                print(f"Loaded {env_key}")
        except subprocess.CalledProcessError as e:
            print(f"Error fetching {env_key}: {e.stderr}", file=sys.stderr)

    with open(ENV_PATH, 'w') as f:
        f.write("\n".join(env_content) + "\n")
    
    print(f"Successfully wrote secrets to {ENV_PATH}")

if __name__ == "__main__":
    main()
