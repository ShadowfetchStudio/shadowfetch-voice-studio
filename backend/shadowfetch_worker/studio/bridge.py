"""Talk to a local VoiceStudio backend over its documented HTTP API.

VoiceStudio (https://github.com/debpalash/VoiceStudio) stays a separate
AGPL-3.0 program. This module only speaks HTTP to it. It does not import
VoiceStudio's Python package.
"""
from __future__ import annotations

import ipaddress
import json
import os
import uuid
from pathlib import Path
from urllib import error, request
from urllib.parse import urlsplit

from ..protocol import ENGINE_UNAVAILABLE, INVALID_PARAMS, OFFLINE_BLOCKED, PERMISSION_DENIED, WorkerError

DEFAULT_URL = "http://127.0.0.1:3900"


def checkout_root() -> Path | None:
    """A VoiceStudio tree next to this app, or ``SFVS_VOICESTUDIO_ROOT``."""
    candidates: list[Path] = []
    env = os.environ.get("SFVS_VOICESTUDIO_ROOT", "").strip()
    if env:
        candidates.append(Path(env).expanduser())
    repo = Path(__file__).resolve().parents[3]
    candidates.append(repo / "third_party" / "VoiceStudio")
    for path in candidates:
        if (path / "backend" / "main.py").is_file():
            return path
    return None


def bundle_info() -> dict:
    root = checkout_root()
    return {
        "bundled": root is not None,
        "root": str(root) if root else None,
        "default_url": DEFAULT_URL,
        "license": "AGPL-3.0-only",
        "upstream": "https://github.com/debpalash/VoiceStudio",
    }


def validate_base_url(url: str, *, offline: bool = False) -> str:
    """Accept loopback HTTP and any HTTPS URL. Refuse credentialed remote HTTP."""
    raw = (url or DEFAULT_URL).strip()
    parts = urlsplit(raw)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise WorkerError(INVALID_PARAMS, "VoiceStudio URL must start with http:// or https://", {"url": raw})
    if parts.username or parts.password:
        raise WorkerError(INVALID_PARAMS, "Put a VoiceStudio API key in the request, not in the URL", {"url": raw})
    loopback = _is_loopback(parts.hostname)
    if parts.scheme == "http" and not loopback:
        raise WorkerError(
            PERMISSION_DENIED,
            "VoiceStudio over plain HTTP is only allowed on this computer. Use https:// for a remote engine.",
            {"url": raw},
            False,
        )
    if offline and not loopback:
        raise WorkerError(
            OFFLINE_BLOCKED,
            "Offline mode blocks a remote VoiceStudio engine. Use the engine on this computer, or turn offline mode off.",
            {"url": raw},
        )
    return raw.rstrip("/")


def status(url: str, *, offline: bool = False, timeout: float = 3.0) -> dict:
    """Probe ``/health`` and the speech capability document. Never raises for a down server."""
    base = validate_base_url(url, offline=offline)
    health = _get_json(f"{base}/health", timeout=timeout)
    caps = _get_json(f"{base}/.well-known/voicestudio-speech", timeout=timeout) if health["ok"] else None
    reachable = bool(health["ok"] and isinstance(health["body"], dict) and health["body"].get("status") == "ok")
    starting = bool(health["status"] == 503 and isinstance(health["body"], dict) and health["body"].get("status") == "starting")
    body = health["body"] if isinstance(health["body"], dict) else {}
    studio_page = body.get("app") == "Shadowfetch Voice Studio" and body.get("voicestudio") != "ok"
    if studio_page:
        reachable = False
        message = "Studio is open in the browser at this address. VoiceStudio's speech engine is not running yet."
    elif reachable:
        message = "VoiceStudio is ready on this computer."
    elif starting:
        message = body.get("label") or "VoiceStudio is still starting."
    elif health["error"]:
        message = "VoiceStudio is not running at that address."
    else:
        message = "VoiceStudio answered, but it is not ready."
    return {
        "url": base,
        "reachable": reachable,
        "starting": starting,
        "status": body.get("status") or ("offline" if health["error"] else "unknown"),
        "version": body.get("version"),
        "device": body.get("device"),
        "protocol": (caps or {}).get("body", {}).get("protocol") if isinstance((caps or {}).get("body"), dict) else None,
        "message": message,
        "bundle": bundle_info(),
    }


def speak(
    url: str,
    text: str,
    *,
    out_path: Path,
    voice: str = "default",
    instruct: str | None = None,
    model: str = "omnivoice",
    offline: bool = False,
    timeout: float = 300.0,
) -> dict:
    """POST ``/v1/audio/speech`` and write the WAV next to the user's other exports."""
    script = (text or "").strip()
    if not script:
        raise WorkerError(INVALID_PARAMS, "Enter the line you want VoiceStudio to speak.")
    if len(script) > 4096:
        raise WorkerError(INVALID_PARAMS, "VoiceStudio accepts up to 4096 characters in one request.", {"chars": len(script)})
    base = validate_base_url(url, offline=offline)
    payload: dict = {"model": model or "omnivoice", "input": script, "voice": voice or "default", "response_format": "wav"}
    if instruct and instruct.strip():
        payload["instruct"] = instruct.strip()
    body, content_type, failure = _post_bytes(f"{base}/v1/audio/speech", payload, timeout=timeout)
    if failure or body is None:
        raise WorkerError(ENGINE_UNAVAILABLE, failure or "VoiceStudio did not return audio.", {"url": base}, True)
    if not body.startswith(b"RIFF") and "audio" not in (content_type or ""):
        detail = body[:300].decode("utf-8", errors="replace")
        raise WorkerError(ENGINE_UNAVAILABLE, f"VoiceStudio did not return audio. {detail}".strip(), {"url": base}, True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + f".{uuid.uuid4().hex[:8]}.partial")
    tmp.write_bytes(body)
    os.replace(tmp, out_path)
    return {"path": str(out_path), "bytes": len(body), "content_type": content_type or "audio/wav", "url": base}


def _is_loopback(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _get_json(url: str, *, timeout: float) -> dict:
    req = request.Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with request.urlopen(req, timeout=timeout) as response:  # noqa: S310 — URL already checked
            raw = response.read()
            status_code = response.status
    except error.HTTPError as exc:
        raw = exc.read()
        status_code = exc.code
    except error.URLError as exc:
        return {"ok": False, "status": 0, "body": None, "error": str(exc.reason)}
    try:
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        body = None
    return {"ok": status_code == 200, "status": status_code, "body": body, "error": None}


def _post_bytes(url: str, payload: dict, *, timeout: float) -> tuple[bytes | None, str, str | None]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={"Accept": "audio/wav, application/json", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:  # noqa: S310
            return response.read(), response.headers.get("Content-Type", ""), None
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        return None, "", f"VoiceStudio returned HTTP {exc.code}. {detail}".strip()
    except error.URLError as exc:
        return None, "", f"VoiceStudio is unavailable: {exc.reason}"
