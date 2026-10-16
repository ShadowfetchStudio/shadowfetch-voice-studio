"""Serve the Studio page on loopback so a browser at the documented address gets a page.

VoiceStudio's own API, when it is running, listens on 127.0.0.1:3901. This
process does not import that project. Speech requests are forwarded only to
that loopback upstream.
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib import error, request
from urllib.parse import urlsplit

from .. import __version__
from .chapters import split_chapters
from .design import describe_voice
from .bridge import _is_loopback

HOST = "127.0.0.1"
DEFAULT_PORT = 3900
MAX_BODY = 1_000_000
APP_NAME = "Shadowfetch Voice Studio"


def upstream_base() -> str:
    """Loopback VoiceStudio API. A non-loopback value is ignored."""
    raw = os.environ.get("SFVS_VOICESTUDIO_UPSTREAM", "http://127.0.0.1:3901").strip()
    parts = urlsplit(raw)
    if parts.scheme != "http" or not parts.hostname or not _is_loopback(parts.hostname):
        return ""
    if parts.username or parts.password:
        return ""
    return raw.rstrip("/")


def upstream_health(timeout: float = 1.5) -> dict | None:
    base = upstream_base()
    if not base:
        return None
    req = request.Request(f"{base}/health", headers={"Accept": "application/json"}, method="GET")
    try:
        with request.urlopen(req, timeout=timeout) as response:  # noqa: S310 — loopback only
            if response.status != 200:
                return None
            body = json.loads(response.read().decode("utf-8"))
    except (error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError, OSError):
        return None
    if isinstance(body, dict) and body.get("status") == "ok":
        return body
    return None


def health_payload() -> dict:
    upstream = upstream_health()
    if upstream:
        return {
            "status": "ok",
            "version": upstream.get("version") or __version__,
            "device": upstream.get("device") or "local",
            "app": APP_NAME,
            "voicestudio": "ok",
        }
    return {
        "status": "ok",
        "version": __version__,
        "device": "local",
        "app": APP_NAME,
        "voicestudio": "offline",
    }


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Shadowfetch Voice Studio</title>
<style>
  :root { color-scheme: dark; --bg: #12141a; --panel: #1c2030; --line: #2c3348; --text: #e8eaf2; --muted: #9aa3b8; --accent: #7aa2ff; }
  * { box-sizing: border-box; }
  body { margin: 0; font: 16px/1.45 "Segoe UI", system-ui, sans-serif; background: var(--bg); color: var(--text); }
  main { max-width: 760px; margin: 0 auto; padding: 32px 20px 64px; display: flex; flex-direction: column; gap: 20px; }
  h1 { font-size: 28px; font-weight: 600; margin: 0; }
  h2 { font-size: 18px; margin: 0; }
  p { margin: 0; }
  .muted { color: var(--muted); }
  section { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
  label { display: flex; flex-direction: column; gap: 6px; font-size: 13px; font-weight: 600; }
  textarea, button { font: inherit; }
  textarea { width: 100%; min-height: 96px; padding: 10px 12px; border-radius: 8px; border: 1px solid var(--line); background: #0e1118; color: var(--text); resize: vertical; }
  button { align-self: flex-start; background: var(--accent); color: #0d1220; border: 0; border-radius: 8px; padding: 8px 14px; font-weight: 600; cursor: pointer; }
  button:disabled { opacity: 0.6; cursor: wait; }
  pre, .result { white-space: pre-wrap; margin: 0; font: 14px/1.45 ui-monospace, monospace; }
  ul { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 10px; }
  li { border-top: 1px solid var(--line); padding-top: 10px; }
</style>
</head>
<body>
<main>
  <header>
    <h1>Shadowfetch Voice Studio</h1>
    <p class="muted" id="status">Checking this computer…</p>
  </header>
  <section>
    <h2>Design a voice</h2>
    <p class="muted">Describe the voice in plain language. This page maps the words locally. It does not download a model.</p>
    <label>Description
      <textarea id="design-text" placeholder="a warm elderly British woman, slightly raspy"></textarea>
    </label>
    <button id="design-go" type="button">Design</button>
    <pre id="design-out" class="result"></pre>
  </section>
  <section>
    <h2>Split a script into chapters</h2>
    <p class="muted">Chapter, Part, or Markdown headings start a new chapter.</p>
    <label>Script
      <textarea id="chapter-text" placeholder="Chapter 1&#10;&#10;Once there was a road."></textarea>
    </label>
    <button id="chapter-go" type="button">Split into chapters</button>
    <ul id="chapter-out"></ul>
  </section>
</main>
<script>
const statusEl = document.getElementById("status");
async function refresh() {
  try {
    const health = await fetch("/health").then((r) => r.json());
    const engine = health.voicestudio === "ok"
      ? "VoiceStudio's speech engine is running."
      : "VoiceStudio's speech engine is not running yet. Start it with scripts/run-voicestudio-api.sh (127.0.0.1:3901).";
    statusEl.textContent = "Studio is open on this computer. " + engine;
  } catch (err) {
    statusEl.textContent = "This page is open, but the status check failed.";
  }
}
async function post(path, body, button) {
  button.disabled = true;
  try {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Request failed");
    return payload;
  } finally {
    button.disabled = false;
  }
}
document.getElementById("design-go").addEventListener("click", async () => {
  const button = document.getElementById("design-go");
  const out = document.getElementById("design-out");
  out.textContent = "";
  try {
    const result = await post("/studio/design", { description: document.getElementById("design-text").value }, button);
    const lines = Object.entries(result.attrs || {}).map(([key, value]) => key + ": " + value);
    if (result.instruct) lines.push("instruct: " + result.instruct);
    if (result.unmatched && result.unmatched.length) lines.push("unmatched: " + result.unmatched.join(", "));
    out.textContent = lines.join("\\n") || "No description to map.";
  } catch (err) {
    out.textContent = err.message;
  }
});
document.getElementById("chapter-go").addEventListener("click", async () => {
  const button = document.getElementById("chapter-go");
  const out = document.getElementById("chapter-out");
  out.replaceChildren();
  try {
    const result = await post("/studio/chapters", { text: document.getElementById("chapter-text").value }, button);
    for (const chapter of result.chapters || []) {
      const item = document.createElement("li");
      const title = document.createElement("strong");
      title.textContent = chapter.title + " (" + chapter.chars + " characters)";
      const body = document.createElement("p");
      body.textContent = chapter.text;
      item.append(title, body);
      out.append(item);
    }
    if (!result.chapters || !result.chapters.length) {
      const item = document.createElement("li");
      item.textContent = "No chapters in that script.";
      out.append(item);
    }
  } catch (err) {
    const item = document.createElement("li");
    item.textContent = err.message;
    out.append(item);
  }
});
refresh();
</script>
</body>
</html>
"""


class StudioHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in {"/", "/index.html"}:
            self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            return
        if path == "/favicon.ico":
            self._send(204, b"", "image/x-icon")
            return
        if path == "/health":
            self._json(200, health_payload())
            return
        if path == "/.well-known/voicestudio-speech":
            upstream = upstream_health()
            self._json(200, {
                "protocol": "shadowfetch.studio.v1",
                "app": APP_NAME,
                "speech": "proxied" if upstream else "offline",
                "upstream": upstream_base() or None,
            })
            return
        self._json(404, {"error": "Not found"})

    def do_POST(self):  # noqa: N802
        path = self.path.split("?", 1)[0]
        raw = self._read_body()
        if raw is None:
            return
        if path == "/v1/audio/speech":
            code, body, content_type = _proxy_speech(raw, self.headers.get("Content-Type", "application/json"))
            self._send(code, body, content_type)
            return
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._json(400, {"error": "Send a JSON body."})
            return
        if not isinstance(payload, dict):
            self._json(400, {"error": "Send a JSON object."})
            return
        if path == "/studio/design":
            self._json(200, describe_voice(str(payload.get("description") or "")))
            return
        if path == "/studio/chapters":
            limit = payload.get("max_chars", 4000)
            try:
                limit = int(limit)
            except (TypeError, ValueError):
                self._json(400, {"error": "max_chars must be a number."})
                return
            chapters = split_chapters(str(payload.get("text") or ""), limit)
            self._json(200, {"chapters": chapters, "count": len(chapters)})
            return
        self._json(404, {"error": "Not found"})

    def _read_body(self) -> bytes | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(400, {"error": "Content-Length must be a number."})
            return None
        if length < 0 or length > MAX_BODY:
            self._json(413, {"error": "That request is too large."})
            return None
        return self.rfile.read(length)

    def _json(self, code: int, payload: dict) -> None:
        self._send(code, json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8")

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.close_connection = True
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        try:
            self.wfile.write(body)
        except OSError:
            return

    def log_message(self, fmt: str, *args) -> None:
        return


def _proxy_speech(body: bytes, content_type: str) -> tuple[int, bytes, str]:
    base = upstream_base()
    if not base or upstream_health() is None:
        message = {
            "error": "VoiceStudio's speech engine is not running. Start it with scripts/run-voicestudio-api.sh on 127.0.0.1:3901.",
        }
        return 503, json.dumps(message).encode("utf-8"), "application/json; charset=utf-8"
    req = request.Request(
        f"{base}/v1/audio/speech",
        data=body,
        headers={"Content-Type": content_type, "Accept": "audio/wav, application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=300) as response:  # noqa: S310 — loopback only
            payload = response.read(52_428_800)
            return response.status, payload, response.headers.get("Content-Type", "application/octet-stream")
    except error.HTTPError as exc:
        payload = exc.read(65_536)
        return exc.code, payload, exc.headers.get("Content-Type", "application/json")
    except (error.URLError, TimeoutError, OSError):
        message = {"error": "VoiceStudio's speech engine stopped answering."}
        return 503, json.dumps(message).encode("utf-8"), "application/json; charset=utf-8"


def make_server(host: str = HOST, port: int | None = None) -> ThreadingHTTPServer:
    """Bind the Studio page. Only loopback hosts are accepted."""
    if not _is_loopback(host):
        raise ValueError("The Studio page binds to this computer only.")
    chosen = DEFAULT_PORT if port is None else port
    if port is None:
        env = os.environ.get("SFVS_STUDIO_PORT", "").strip()
        if env:
            try:
                chosen = int(env)
            except ValueError as exc:
                raise ValueError("SFVS_STUDIO_PORT must be a number.") from exc
    if chosen < 0 or chosen > 65535:
        raise ValueError("The Studio page port must be between 0 and 65535.")
    server = ThreadingHTTPServer((host, chosen), StudioHandler)
    server.daemon_threads = True
    return server


def main() -> None:
    server = make_server()
    host, port = server.server_address[:2]
    print(f"Shadowfetch Voice Studio is at http://{host}:{port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
