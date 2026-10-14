"""studio.* — the merged Shadowfetch + VoiceStudio workspaces."""
from __future__ import annotations

import time
import uuid
from typing import Any

from pydantic import BaseModel, Field

from ..rpc import Ctx, method
from ..studio.bridge import DEFAULT_URL, bundle_info, speak, status
from ..studio.chapters import split_chapters
from ..studio.design import describe_voice
from ..studio.dub import cues_from_segments, script_from_cues

APP_VERSION = "0.3.0"

WORKSPACES = (
    {"id": "speak", "title": "Speak", "summary": "Type, pick a cloned voice, and hear it. Qwen3-TTS on this computer.", "engine": "shadowfetch"},
    {"id": "design", "title": "Design", "summary": "Describe a voice in words. Shadowfetch parses the description; VoiceStudio can speak it.", "engine": "both"},
    {"id": "dub", "title": "Dub", "summary": "Transcribe a recording into timed lines, edit them, and send the script to Speak.", "engine": "shadowfetch"},
    {"id": "dictate", "title": "Dictate", "summary": "Record with the microphone and turn it into text with local Whisper.", "engine": "shadowfetch"},
    {"id": "transcribe", "title": "Transcribe", "summary": "Turn an audio file into text without leaving the studio.", "engine": "shadowfetch"},
    {"id": "audiobook", "title": "Audiobook", "summary": "Split a long script into chapters and open each one in Speak.", "engine": "shadowfetch"},
)


def _settings(ctx: Ctx):
    return ctx.server.state["settings"].value


class DesignParams(BaseModel):
    description: str = ""


class ChapterParams(BaseModel):
    text: str = ""
    max_chars: int = 4000


class DubParams(BaseModel):
    segments: list[dict[str, Any]] = Field(default_factory=list)


class ScriptParams(BaseModel):
    cues: list[dict[str, Any]] = Field(default_factory=list)


class VoiceStudioParams(BaseModel):
    url: str | None = None


class VoiceStudioSpeakParams(BaseModel):
    text: str
    url: str | None = None
    voice: str = "default"
    instruct: str | None = None
    model: str = "omnivoice"


def _url(ctx: Ctx, explicit: str | None) -> str:
    settings = _settings(ctx)
    return (explicit or getattr(settings, "voicestudio_url", None) or DEFAULT_URL).strip()


@method("studio.catalog")
def studio_catalog(ctx: Ctx, params: dict[str, Any]) -> dict[str, Any]:
    settings = _settings(ctx)
    return {
        "app": "Shadowfetch Voice Studio",
        "version": APP_VERSION,
        "workspaces": list(WORKSPACES),
        "voicestudio_url": getattr(settings, "voicestudio_url", DEFAULT_URL),
        "voicestudio": bundle_info(),
    }


@method("studio.design", params=DesignParams)
def studio_design(ctx: Ctx, p: DesignParams) -> dict[str, Any]:
    return describe_voice(p.description)


@method("studio.chapters", params=ChapterParams)
def studio_chapters(ctx: Ctx, p: ChapterParams) -> dict[str, Any]:
    chapters = split_chapters(p.text, p.max_chars)
    return {"chapters": chapters, "count": len(chapters)}


@method("studio.dub_cues", params=DubParams)
def studio_dub_cues(ctx: Ctx, p: DubParams) -> dict[str, Any]:
    cues = cues_from_segments(p.segments)
    return {"cues": cues, "count": len(cues), "script": script_from_cues(cues)}


@method("studio.script", params=ScriptParams)
def studio_script(ctx: Ctx, p: ScriptParams) -> dict[str, Any]:
    script = script_from_cues(p.cues)
    return {"script": script, "chars": len(script)}


@method("studio.voicestudio.status", params=VoiceStudioParams)
def studio_voicestudio_status(ctx: Ctx, p: VoiceStudioParams) -> dict[str, Any]:
    settings = _settings(ctx)
    return status(_url(ctx, p.url), offline=bool(settings.offline))


@method("studio.voicestudio.speak", params=VoiceStudioSpeakParams)
def studio_voicestudio_speak(ctx: Ctx, p: VoiceStudioSpeakParams) -> dict[str, Any]:
    settings = _settings(ctx)
    paths = ctx.server.state["paths"]
    dest = paths.exports / "voicestudio" / f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}.wav"
    ctx.progress("voicestudio", "Asking VoiceStudio to speak")
    result = speak(
        _url(ctx, p.url),
        p.text,
        out_path=dest,
        voice=p.voice,
        instruct=p.instruct,
        model=p.model,
        offline=bool(settings.offline),
    )
    result["elapsed_s"] = round(time.time() - ctx.started_at, 3)
    return result
