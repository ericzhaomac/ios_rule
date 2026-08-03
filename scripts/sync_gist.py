from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import json
import os
import sys


GITHUB_API = "https://api.github.com"
DEFAULT_FILENAME = "msub_aggregated.ini"


def github_request(url: str, token: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ios_rule-gist-sync/1.0",
        },
    )
    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def upsert_gist(file_path: Path, token: str, gist_id: str | None) -> dict:
    content = file_path.read_text(encoding="utf-8")
    payload = {
        "description": "Aggregated ios_rule msub generated from source gist",
        "public": False,
        "files": {DEFAULT_FILENAME: {"content": content}},
    }
    if gist_id:
        return github_request(f"{GITHUB_API}/gists/{gist_id}", token, method="PATCH", payload=payload)
    return github_request(f"{GITHUB_API}/gists", token, method="POST", payload=payload)


def main() -> int:
    token = os.getenv("GIST_TOKEN") or os.getenv("GH_TOKEN")
    gist_id = os.getenv("AGGREGATED_GIST_ID")
    file_path = Path(os.getenv("AGGREGATED_CONFIG_PATH", "msub_aggregated.ini"))

    if not token:
        print("Missing GIST_TOKEN or GH_TOKEN", file=sys.stderr)
        return 1
    if not file_path.exists():
        print(f"Missing aggregated config: {file_path}", file=sys.stderr)
        return 1

    gist = upsert_gist(file_path, token, gist_id)
    print(json.dumps({"id": gist["id"], "html_url": gist["html_url"], "files": list(gist["files"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
