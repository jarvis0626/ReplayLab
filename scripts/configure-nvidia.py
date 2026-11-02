"""Configure a server-only NVIDIA credential without shell history or echo."""

import argparse
import os
import sys
from getpass import getpass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))


def main():
    from dotenv import dotenv_values, set_key

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replace", action="store_true", help="Prompt for a replacement key using hidden input.")
    args = parser.parse_args()
    target = ROOT / "apps" / "api" / ".env"
    existing = dotenv_values(target) if target.exists() else {}
    credential = None if args.replace else os.environ.get("NVIDIA_API_KEY") or existing.get("NVIDIA_API_KEY")
    if not credential:
        credential = getpass("NVIDIA API key (hidden): ").strip()
    if not credential or not credential.startswith("nvapi-") or any(c.isspace() for c in credential):
        raise SystemExit("A nonempty NVIDIA API key is required; nothing was saved.")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.touch(exist_ok=True)
    set_key(str(target), "NVIDIA_API_KEY", credential)
    set_key(str(target), "AI_PROVIDER", "nvidia")
    set_key(str(target), "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    set_key(str(target), "NVIDIA_MODEL", "meta/muse-glimmer-30b")
    print("NVIDIA credential configured in ignored apps/api/.env; value not displayed.")
    print("Restart the API service to load configuration changes.")
    if not args.replace:
        print("To enter a replacement key, rerun this script with --replace.")


if __name__ == "__main__":
    main()
