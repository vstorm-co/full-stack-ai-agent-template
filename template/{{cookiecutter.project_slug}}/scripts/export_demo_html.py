#!/usr/bin/env python3
"""Export a saved agent conversation to a single, self-contained HTML replay.

The output is one offline `.html` file: open it (double-click) and press Play to
watch the agent's saved run animate step-by-step — tools spin up, results land,
charts render, the answer types out — with no server, no network and no live
model call. Ideal for sharing a demo (e.g. dropping it on Google Drive).

Everything the replay needs (messages + tool calls + chart/map specs) is already
persisted in the conversation, so the export is a pure data + template merge.

Sources (pick one):
    --url URL     Fetch a conversation JSON from a running backend, e.g.
                  http://localhost:{{ cookiecutter.backend_port }}/api/v1/demos/<id>   (public demo endpoint)
    --id UUID     Shorthand for the demo endpoint on --base-url (default localhost:{{ cookiecutter.backend_port }})
    --json FILE   A JSON file: either the API response object, or a bare message array

Examples:
    # From the public demo endpoint of a running dev server
    python scripts/export_demo_html.py --id 3f2c... -o ecommerce_sale.html

    # From a saved JSON payload (curl'd earlier, or exported by hand)
    curl -s localhost:{{ cookiecutter.backend_port }}/api/v1/demos/3f2c... > conv.json
    python scripts/export_demo_html.py --json conv.json -o ecommerce_sale.html
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# The real, bundled template: the exact app components (DemoReplay + Recharts +
# globals.css) compiled to one self-contained HTML by the frontend Vite target.
# Built with:  cd frontend && bun run build:demo-export
REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLED_TEMPLATE = REPO_ROOT / "frontend" / "demo-export" / "dist" / "index.html"
FRONTEND_DIR = REPO_ROOT / "frontend"


def _load_url(url: str) -> Any:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (trusted local URL)
        return json.loads(resp.read().decode("utf-8"))


_MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}


def _avatar_data_uri(src: str) -> str:
    """Read an avatar (local path or http URL) and return a base64 data URI."""
    import base64
    import mimetypes

    if src.startswith(("http://", "https://")):
        with urllib.request.urlopen(src, timeout=30) as resp:  # noqa: S310
            raw = resp.read()
            mime = resp.headers.get_content_type() or "image/png"
    else:
        path = Path(src)
        if not path.exists():
            raise SystemExit(f"Avatar file not found: {path}")
        raw = path.read_bytes()
        mime = _MIME_BY_EXT.get(path.suffix.lower()) or mimetypes.guess_type(str(path))[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


def _extract(payload: Any) -> tuple[list[dict[str, Any]], str]:
    """Pull (messages, title) out of whatever JSON shape we were given."""
    if isinstance(payload, list):
        return payload, ""
    if isinstance(payload, dict):
        title = str(payload.get("title") or "")
        for key in ("messages", "items"):
            msgs = payload.get(key)
            if isinstance(msgs, list):
                return msgs, title
    raise SystemExit("Could not find a message list in the input (expected an array, or an object with a 'messages' field).")


def _normalize(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Shape messages into the RawMessage form the app's conversation-to-chat expects.

    Tolerates both the API payload (tool_call_id/tool_name) and looser inputs, and
    fills the ids/timestamps the real components read so nothing renders as broken.
    """
    out: list[dict[str, Any]] = []
    for i, m in enumerate(messages):
        raw_calls = m.get("tool_calls") or []
        calls = []
        for j, tc in enumerate(raw_calls):
            calls.append(
                {
                    "tool_call_id": tc.get("tool_call_id") or tc.get("id") or f"tc-{i}-{j}",
                    "tool_name": tc.get("tool_name") or tc.get("name") or "tool",
                    "args": tc.get("args") or {},
                    "result": tc.get("result"),
                    "status": tc.get("status") or "completed",
                }
            )
        out.append(
            {
                "id": m.get("id") or f"m-{i}",
                "conversation_id": m.get("conversation_id") or "demo",
                "role": m.get("role", "assistant"),
                "content": m.get("content") or "",
                "thinking": m.get("thinking") or None,
                "created_at": m.get("created_at") or "2026-01-01T00:00:00Z",
                "tool_calls": calls,
                "files": m.get("files"),
            }
        )
    return out


def _ensure_bundle(rebuild: bool) -> Path:
    """Build the Vite single-file bundle before exporting.

    Rebuilds by default so a demo never ships a stale UI built from older source; pass
    ``--no-rebuild`` to reuse the existing bundle when it is known to be current.
    """
    if rebuild or not BUNDLED_TEMPLATE.exists():
        print("• Building the demo-export bundle (frontend/demo-export)…")
        subprocess.run(["bun", "run", "build:demo-export"], cwd=FRONTEND_DIR, check=True)
    if not BUNDLED_TEMPLATE.exists():
        raise SystemExit(
            f"Bundle not found at {BUNDLED_TEMPLATE}.\n"
            "Build it once with:  cd frontend && bun run build:demo-export"
        )
    return BUNDLED_TEMPLATE


def build_html(messages: list[dict[str, Any]], title: str, theme: str, avatar: str, rebuild: bool) -> str:
    template = _ensure_bundle(rebuild).read_text(encoding="utf-8")
    data_json = json.dumps(messages, ensure_ascii=False)
    # Neutralize any literal </script> that could close the <script> data block.
    data_json = data_json.replace("</", "<\\/")
    safe_title = re.sub(r"[<>]", "", (title or "Agent session").strip()) or "Agent session"
    if "__DEMO_DATA__" not in template:
        raise SystemExit("Template is missing the __DEMO_DATA__ marker — drop --no-rebuild so the bundle rebuilds.")
    # Single-pass substitution: replace every sentinel in one scan of the template so a
    # marker that happens to appear inside an injected value (e.g. a message body that
    # contains the literal "__DEMO_THEME__") is never rewritten by a later pass.
    replacements = {
        "__DEMO_DATA__": data_json,
        "__DEMO_TITLE__": safe_title,
        "__DEMO_THEME__": theme,
        "__DEMO_USER_AVATAR__": avatar,  # data URI, or "" for the default icon
    }
    pattern = re.compile("|".join(re.escape(marker) for marker in replacements))
    return pattern.sub(lambda m: replacements[m.group(0)], template)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="Conversation JSON URL from a running backend")
    src.add_argument("--id", help="Demo conversation UUID (uses --base-url + /api/v1/demos/<id>)")
    src.add_argument("--json", dest="json_file", help="Path to a JSON file (API response or message array)")
    ap.add_argument("--base-url", default="http://localhost:{{ cookiecutter.backend_port }}", help="Backend base URL for --id (default: %(default)s)")
    ap.add_argument("-o", "--out", help="Output HTML path (default: derived from title / demo.html)")
    ap.add_argument("--title", help="Override the replay title shown in the header")
    ap.add_argument(
        "--theme",
        choices=["light", "dark", "system"],
        default="light",
        help="Color theme of the export (default: light; 'system' follows the viewer's OS)",
    )
    ap.add_argument(
        "--avatar",
        help="Image (local path or http URL) to use as the user-message avatar; embedded as a data URI",
    )
    ap.add_argument(
        "--no-rebuild",
        action="store_true",
        help="Reuse the existing Vite bundle instead of rebuilding it first (faster, but risks a stale UI)",
    )
    args = ap.parse_args()

    try:
        if args.url:
            payload = _load_url(args.url)
        elif args.id:
            payload = _load_url(f"{args.base_url.rstrip('/')}/api/v1/demos/{args.id}")
        else:
            payload = json.loads(Path(args.json_file).read_text(encoding="utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404 and args.id:
            raise SystemExit(
                f"404 for conversation {args.id}.\n"
                "The public demo endpoint only serves conversations flagged as a demo.\n"
                "Fix: open /admin/conversations, toggle 'demo' on this conversation "
                "(sets is_demo=True), then re-run. Also double-check the id is correct."
            ) from exc
        raise SystemExit(f"HTTP {exc.code} fetching the conversation: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"Could not reach the backend ({exc.reason}). Is it running on {args.base_url}? "
            "Start it (make dev) or pass --base-url / --json."
        ) from exc

    messages, title = _extract(payload)
    if args.title:
        title = args.title
    messages = _normalize(messages)
    if not messages:
        raise SystemExit("No messages found — nothing to export.")

    avatar = _avatar_data_uri(args.avatar) if args.avatar else ""
    html = build_html(messages, title, args.theme, avatar, rebuild=not args.no_rebuild)

    if args.out:
        out = Path(args.out)
    else:
        slug = re.sub(r"[^a-z0-9]+", "-", (title or "demo").lower()).strip("-") or "demo"
        out = Path(f"{slug}.html")
    out.write_text(html, encoding="utf-8")

    kb = len(html.encode("utf-8")) / 1024
    print(f"✓ Wrote {out}  ({len(messages)} messages, {kb:.0f} KB, self-contained)")
    print("  Open it in any browser — no server needed. Press Play to watch the replay.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
