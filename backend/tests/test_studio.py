"""Merged studio: design, chapters, dub cues, and the VoiceStudio HTTP bridge."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from shadowfetch_worker.protocol import WorkerError
from shadowfetch_worker.studio.chapters import split_chapters
from shadowfetch_worker.studio.design import describe_voice
from shadowfetch_worker.studio.dub import cues_from_segments, script_from_cues
from shadowfetch_worker.studio.bridge import speak, status, validate_base_url


def test_design_maps_a_description_and_keeps_unknown_words():
    result = describe_voice("a warm elderly British woman, slightly raspy")
    assert result["attrs"]["gender"] == "female"
    assert result["attrs"]["age"] == "older"
    assert result["attrs"]["tone"] == "warm"
    assert result["attrs"]["accent"] == "british"
    assert result["attrs"]["pitch"] == "auto"
    assert "warm" in result["instruct"]
    assert "raspy" in result["unmatched"]
    assert describe_voice("   ")["instruct"] == ""


def test_chapters_follow_headings_and_pack_long_text():
    text = "Chapter 1\n\nOnce there was a road.\n\nChapter 2\n\nThen it ended."
    chapters = split_chapters(text, max_chars=4000)
    assert [c["title"] for c in chapters] == ["Chapter 1", "Chapter 2"]
    assert chapters[0]["text"] == "Once there was a road."

    long = "Para one is here.\n\n" + ("word " * 80)
    packed = split_chapters(long, max_chars=200)
    assert packed[0]["title"].startswith("Chapter 1")
    assert all(c["chars"] <= 200 for c in packed)
    assert sum(c["chars"] for c in packed) > 200
    assert split_chapters("  \n") == []


def test_dub_cues_keep_timing_and_rebuild_a_script():
    cues = cues_from_segments([
        {"start": 0.0, "end": 1.5, "text": " Hello "},
        {"start": 2.0, "end": 3.0, "text": "there"},
        {"text": ""},
        {"text": "untimed"},
    ])
    assert cues[0]["gap_after_s"] == 0.5
    assert cues[1]["duration_s"] == 1.0
    assert cues[2]["start_s"] is None
    assert script_from_cues(cues) == "Hello\n\nthere\n\nuntimed"


def test_bridge_refuses_remote_http_and_offline_remote():
    with pytest.raises(WorkerError) as remote:
        validate_base_url("http://example.com:3900")
    assert remote.value.code == "PERMISSION_DENIED"
    with pytest.raises(WorkerError) as offline:
        validate_base_url("https://voice.example", offline=True)
    assert offline.value.code == "OFFLINE_BLOCKED"
    assert validate_base_url("http://127.0.0.1:3900/").endswith(":3900")


def test_bridge_status_and_speak_against_a_local_server(tmp_path):
    wav = b"RIFF" + b"\x00" * 12 + b"WAVEfmt "

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if self.path == "/health":
                body = json.dumps({"status": "ok", "version": "test", "device": "cpu"}).encode()
                self._send(200, body, "application/json")
            elif self.path == "/.well-known/voicestudio-speech":
                body = json.dumps({"protocol": "voicestudio.speech.v1"}).encode()
                self._send(200, body, "application/json")
            else:
                self._send(404, b"{}", "application/json")

        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            assert payload["input"] == "Hello from Shadowfetch"
            assert payload["instruct"] == "warm, female"
            self._send(200, wav, "audio/wav")

        def _send(self, code, body, content_type):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        probed = status(url)
        assert probed["reachable"] is True
        assert probed["version"] == "test"
        assert probed["protocol"] == "voicestudio.speech.v1"
        out = tmp_path / "line.wav"
        spoken = speak(url, "Hello from Shadowfetch", out_path=out, instruct="warm, female")
        assert spoken["bytes"] == len(wav)
        assert out.read_bytes() == wav
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_status_reports_a_missing_engine():
    probed = status("http://127.0.0.1:1")
    assert probed["reachable"] is False
    assert "not running" in probed["message"]


def test_studio_page_serves_html_and_does_not_redirect():
    from urllib import request as urlrequest

    from shadowfetch_worker.studio.serve import make_server

    with pytest.raises(ValueError, match="this computer only"):
        make_server("0.0.0.0", 0)

    server = make_server("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        class NoRedirect(urlrequest.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                raise AssertionError(f"unexpected redirect to {newurl}")

        opener = urlrequest.build_opener(NoRedirect)
        with opener.open(base + "/", timeout=3) as response:
            page = response.read().decode("utf-8")
            assert response.status == 200
            assert "text/html" in response.headers.get("Content-Type", "")
            assert response.geturl() == base + "/"
            assert not response.headers.get("Location")
        assert "<h1>Shadowfetch Voice Studio</h1>" in page
        assert "http-equiv=\"refresh\"" not in page

        with opener.open(base + "/health", timeout=3) as response:
            health = json.loads(response.read().decode("utf-8"))
        assert health["status"] == "ok"
        assert health["app"] == "Shadowfetch Voice Studio"
        assert health["voicestudio"] == "offline"

        with opener.open(base + "/favicon.ico", timeout=3) as response:
            assert response.status == 204

        with opener.open(base + "/.well-known/voicestudio-speech", timeout=3) as response:
            caps = json.loads(response.read().decode("utf-8"))
        assert caps["protocol"] == "shadowfetch.studio.v1"
        assert caps["speech"] == "offline"

        design = json.dumps({"description": "a warm elderly British woman"}).encode()
        req = urlrequest.Request(base + "/studio/design", data=design, headers={"Content-Type": "application/json"})
        with opener.open(req, timeout=3) as response:
            designed = json.loads(response.read().decode("utf-8"))
        assert designed["attrs"]["gender"] == "female"

        chapters = json.dumps({"text": "Chapter 1\n\nOnce there was a road.\n\nChapter 2\n\nThen it ended."}).encode()
        req = urlrequest.Request(base + "/studio/chapters", data=chapters, headers={"Content-Type": "application/json"})
        with opener.open(req, timeout=3) as response:
            split = json.loads(response.read().decode("utf-8"))
        assert split["count"] == 2
        assert [c["title"] for c in split["chapters"]] == ["Chapter 1", "Chapter 2"]

        probed = status(base)
        assert probed["reachable"] is False
        assert "Studio is open in the browser" in probed["message"]

        speech = urlrequest.Request(
            base + "/v1/audio/speech",
            data=json.dumps({"input": "Hello"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            opener.open(speech, timeout=3)
            raise AssertionError("speech should fail while the engine is down")
        except urlrequest.HTTPError as exc:
            assert exc.code == 503
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_studio_page_forwards_speech_when_the_engine_is_up(monkeypatch):
    from urllib import request as urlrequest

    from shadowfetch_worker.studio import serve as studio_serve

    wav = b"RIFF" + b"\x00" * 12 + b"WAVEfmt "

    class Engine(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if self.path == "/health":
                body = json.dumps({"status": "ok", "version": "engine-test", "device": "cpu"}).encode()
                self._send(200, body, "application/json")
            else:
                self._send(404, b"{}", "application/json")

        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            assert payload["input"] == "Hello from the page"
            self._send(200, wav, "audio/wav")

        def _send(self, code, body, content_type):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            return

    engine = ThreadingHTTPServer(("127.0.0.1", 0), Engine)
    engine_thread = threading.Thread(target=engine.serve_forever, daemon=True)
    engine_thread.start()
    monkeypatch.setenv("SFVS_VOICESTUDIO_UPSTREAM", f"http://127.0.0.1:{engine.server_address[1]}")
    page = studio_serve.make_server("127.0.0.1", 0)
    page_thread = threading.Thread(target=page.serve_forever, daemon=True)
    page_thread.start()
    base = f"http://127.0.0.1:{page.server_address[1]}"
    try:
        with urlrequest.urlopen(base + "/health", timeout=3) as response:
            health = json.loads(response.read().decode("utf-8"))
        assert health["voicestudio"] == "ok"
        assert health["version"] == "engine-test"

        probed = status(base)
        assert probed["reachable"] is True
        assert probed["message"] == "VoiceStudio is ready on this computer."

        speech = urlrequest.Request(
            base + "/v1/audio/speech",
            data=json.dumps({"input": "Hello from the page"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlrequest.urlopen(speech, timeout=3) as response:
            assert response.read() == wav
            assert "audio/wav" in response.headers.get("Content-Type", "")
    finally:
        page.shutdown()
        engine.shutdown()
        page_thread.join(timeout=2)
        engine_thread.join(timeout=2)


def test_studio_methods_are_registered(app):
    import shadowfetch_worker.jobs.studio  # noqa: F401
    from shadowfetch_worker.rpc import registry
    names = set(registry())
    for name in ("studio.catalog", "studio.design", "studio.chapters", "studio.dub_cues", "studio.script",
                 "studio.voicestudio.status", "studio.voicestudio.speak"):
        assert name in names
    result = app.call("studio.design", {"description": "a calm young man"}) if hasattr(app, "call") else None
    if result is None:
        from shadowfetch_worker.jobs.studio import studio_design, DesignParams
        from shadowfetch_worker.rpc import Ctx
        ctx = Ctx(req_id="studio-1", method="studio.design", transport=app.transport, server=app)
        result = studio_design(ctx, DesignParams(description="a calm young man"))
    assert result["attrs"]["gender"] == "male"
    assert result["attrs"]["tone"] == "calm"
