from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKEN_MARKER = "REFRESH TOKEN:"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a Google Calendar OAuth refresh token."
    )
    parser.add_argument(
        "--client-secrets",
        help=(
            "Path to the OAuth desktop client JSON. Defaults to "
            "GOOGLE_OAUTH_CLIENT_SECRET_FILE or the first client_secret*.json file."
        ),
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Env file to update when --write-env is used. Defaults to .env.",
    )
    parser.add_argument(
        "--write-env",
        action="store_true",
        help="Write GOOGLE_OAUTH_CLIENT_JSON and GOOGLE_OAUTH_REFRESH_TOKEN to .env.",
    )
    args = parser.parse_args()

    client_secrets_path = _resolve_client_secrets_path(args.client_secrets)
    client_config = _load_client_config(client_secrets_path)

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    credentials = flow.run_local_server(
        port=0,
        access_type="offline",
        prompt="consent",
    )

    if not credentials.refresh_token:
        raise RuntimeError(
            "Google did not return a refresh token. Re-run with prompt=consent "
            "or revoke the app access in your Google account and try again."
        )

    compact_client_json = json.dumps(client_config, separators=(",", ":"))
    print("GOOGLE_OAUTH_CLIENT_JSON:")
    print(compact_client_json)
    print(TOKEN_MARKER)
    print(credentials.refresh_token)

    if args.write_env:
        _update_env_file(
            Path(args.env_file),
            {
                "GOOGLE_OAUTH_CLIENT_JSON": compact_client_json,
                "GOOGLE_OAUTH_REFRESH_TOKEN": credentials.refresh_token,
            },
        )
        print(f"Updated {args.env_file}")

    return 0


def _resolve_client_secrets_path(configured_path: str | None) -> Path:
    raw_path = configured_path or os.getenv("GOOGLE_OAUTH_CLIENT_SECRET_FILE")
    if raw_path:
        path = Path(raw_path).expanduser()
        if path.is_file():
            return path
        raise FileNotFoundError(f"OAuth client JSON not found: {path}")

    matches = sorted(glob.glob("client_secret*.json"))
    if not matches:
        raise FileNotFoundError(
            "No client_secret*.json file found. Download an OAuth desktop client "
            "JSON from Google Cloud and place it in the project root, or pass "
            "--client-secrets PATH."
        )
    return Path(matches[0])


def _load_client_config(path: Path) -> dict:
    try:
        client_config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"OAuth client JSON is not valid JSON: {path}") from exc

    client_info = client_config.get("installed") or client_config.get("web")
    if not isinstance(client_info, dict):
        raise ValueError("OAuth client JSON must contain an 'installed' or 'web' object.")
    if not client_info.get("client_id") or not client_info.get("client_secret"):
        raise ValueError("OAuth client JSON is missing client_id or client_secret.")

    return client_config


def _update_env_file(path: Path, values: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = [
        line
        for line in lines
        if not any(line.startswith(f"{name}=") for name in values)
    ]
    for name, value in values.items():
        remaining.append(f"{name}={value}")
    path.write_text("\n".join(remaining) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
