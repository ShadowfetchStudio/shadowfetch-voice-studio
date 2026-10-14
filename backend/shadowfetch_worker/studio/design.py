"""Turn a plain-language voice description into a small design recipe.

This is Shadowfetch's own matcher. It does not load a model and it does not
copy VoiceStudio's instruct taxonomy. Tokens are stable English words the
Studio screen can show, store, and forward as style notes to a VoiceStudio
engine when one is running.
"""
from __future__ import annotations

import re

# More specific phrases are listed before the shorter words they contain.
_RULES: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    ("gender", (
        ("non-binary", "neutral"),
        ("nonbinary", "neutral"),
        ("female", "female"),
        ("woman", "female"),
        ("girl", "female"),
        ("male", "male"),
        ("man", "male"),
        ("boy", "male"),
    )),
    ("age", (
        ("middle-aged", "middle-aged"),
        ("middle aged", "middle-aged"),
        ("elderly", "older"),
        ("senior", "older"),
        ("older", "older"),
        ("teenager", "young"),
        ("teen", "young"),
        ("child", "child"),
        ("young", "young"),
    )),
    ("pitch", (
        ("very low", "very-low"),
        ("very high", "very-high"),
        ("deep", "low"),
        ("low", "low"),
        ("high", "high"),
        ("soprano", "high"),
    )),
    ("pace", (
        ("very slow", "very-slow"),
        ("very fast", "very-fast"),
        ("slow", "slow"),
        ("fast", "fast"),
        ("quick", "fast"),
    )),
    ("tone", (
        ("storyteller", "narrative"),
        ("narrator", "narrative"),
        ("whisper", "soft"),
        ("soft", "soft"),
        ("warm", "warm"),
        ("bright", "bright"),
        ("calm", "calm"),
        ("serious", "serious"),
        ("cheerful", "cheerful"),
    )),
    ("accent", (
        ("british", "british"),
        ("english accent", "british"),
        ("american", "american"),
        ("australian", "australian"),
        ("irish", "irish"),
        ("scottish", "scottish"),
        ("indian", "indian"),
    )),
)

_STOP = {
    "a", "an", "the", "and", "or", "with", "voice", "sound", "sounds", "like",
    "of", "to", "for", "who", "that", "is", "slightly", "very", "bit", "little",
}


def describe_voice(description: str) -> dict:
    """Map free text onto one token per category. Unrecognised words stay visible."""
    raw = (description or "").strip()
    folded = re.sub(r"\s+", " ", raw.lower())
    attrs = {category: "auto" for category, _rules in _RULES}
    matched: list[dict[str, str]] = []
    consumed: list[tuple[int, int]] = []

    for category, rules in _RULES:
        best: tuple[int, str, str] | None = None
        for phrase, token in rules:
            start = folded.find(phrase)
            if start < 0:
                continue
            if best is None or start < best[0] or (start == best[0] and len(phrase) > len(best[1])):
                best = (start, phrase, token)
        if best is None:
            continue
        start, phrase, token = best
        attrs[category] = token
        matched.append({"category": category, "token": token, "phrase": phrase})
        consumed.append((start, start + len(phrase)))

    unmatched = _unmatched(folded, consumed)
    instruct = ", ".join(item["token"] for item in matched)
    return {
        "description": raw,
        "attrs": attrs,
        "instruct": instruct,
        "matched": matched,
        "unmatched": unmatched,
    }


def _unmatched(folded: str, consumed: list[tuple[int, int]]) -> list[str]:
    mask = [False] * len(folded)
    for start, end in consumed:
        for i in range(start, min(end, len(mask))):
            mask[i] = True
    leftover = "".join(ch if not mask[i] else " " for i, ch in enumerate(folded))
    words = []
    for word in re.findall(r"[a-z][a-z'-]{2,}", leftover):
        if word in _STOP or word in words:
            continue
        words.append(word)
    return words
