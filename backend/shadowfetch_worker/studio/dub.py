"""Build a dubbing cue sheet from a transcription."""
from __future__ import annotations


def cues_from_segments(segments: list[dict] | None) -> list[dict]:
    """Turn timestamped transcript lines into editable dub cues.

    Each cue keeps the source timing. ``gap_after_s`` is the silence before the
    next line (0 when lines overlap or touch). Lines without timing are kept,
    in order, with ``start_s`` and ``end_s`` left null.
    """
    cues: list[dict] = []
    for raw in segments or []:
        text = str(raw.get("text") or "").strip()
        if not text:
            continue
        start = _seconds(raw.get("start", raw.get("start_s")))
        end = _seconds(raw.get("end", raw.get("end_s")))
        duration = None
        if start is not None and end is not None and end >= start:
            duration = round(end - start, 3)
        cues.append({
            "index": len(cues),
            "start_s": start,
            "end_s": end,
            "duration_s": duration,
            "text": text,
            "gap_after_s": None,
        })
    for i, cue in enumerate(cues):
        nxt = cues[i + 1] if i + 1 < len(cues) else None
        if cue["end_s"] is None or nxt is None or nxt["start_s"] is None:
            cue["gap_after_s"] = None
        else:
            cue["gap_after_s"] = round(max(0.0, nxt["start_s"] - cue["end_s"]), 3)
    return cues


def script_from_cues(cues: list[dict] | None) -> str:
    """Join cue text into a script the existing Speak pipeline can read."""
    lines = [str(c.get("text") or "").strip() for c in (cues or [])]
    return "\n\n".join(line for line in lines if line)


def _seconds(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number < 0:
        return None
    return round(number, 3)
