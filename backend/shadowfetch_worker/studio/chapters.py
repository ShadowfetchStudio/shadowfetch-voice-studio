"""Split a long script into audiobook chapters without calling an engine."""
from __future__ import annotations

import re

_HEADING = re.compile(
    r"(?im)^(?:#{1,3}\s+|(?:chapter|part)\s+\d+\b[^\n]*)"
)


def split_chapters(text: str, max_chars: int = 4000) -> list[dict]:
    """Return chapters in reading order. Blank input yields an empty list.

    Explicit headings (Markdown or ``Chapter N`` / ``Part N``) start a chapter.
    A chapter longer than ``max_chars`` is packed into several parts on paragraph
    boundaries. Text with no headings is packed the same way under ``Chapter 1``.
    """
    raw = (text or "").replace("\r\n", "\n").strip()
    if not raw:
        return []
    limit = max(200, int(max_chars))
    blocks = _blocks(raw)
    chapters: list[dict] = []
    for title, body in blocks:
        pieces = _pack(body, limit)
        total = len(pieces)
        for i, piece in enumerate(pieces, start=1):
            label = title if total == 1 else f"{title} · part {i}"
            chapters.append({
                "index": len(chapters),
                "title": label,
                "text": piece,
                "chars": len(piece),
            })
    return chapters


def _blocks(raw: str) -> list[tuple[str, str]]:
    matches = list(_HEADING.finditer(raw))
    if not matches:
        return [("Chapter 1", raw)]
    blocks: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        preface = raw[: matches[0].start()].strip()
        if preface:
            blocks.append(("Opening", preface))
    for i, match in enumerate(matches):
        title = re.sub(r"^#+\s*", "", match.group(0)).strip() or f"Chapter {i + 1}"
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        body = raw[match.end():end].strip()
        blocks.append((title, body or title))
    return blocks


def _pack(body: str, limit: int) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    if not paragraphs:
        paragraphs = [body.strip()]
    parts: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > limit:
            if current:
                parts.append(current)
                current = ""
            for start in range(0, len(paragraph), limit):
                parts.append(paragraph[start:start + limit].strip())
            continue
        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= limit:
            current = candidate
        else:
            parts.append(current)
            current = paragraph
    if current:
        parts.append(current)
    return [p for p in parts if p]
