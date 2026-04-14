from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


@dataclass(slots=True)
class PageText:
    page_number: int
    text: str
    heading_hints: list[str]


STRUCTURAL_HEADING_RE = re.compile(
    r"(?i)\b("
    r"title\s+[A-Z0-9IVXLC]+"
    r"|chapter\s+[A-Z0-9IVXLC]+"
    r"|section\s+[A-Z0-9IVXLC]+"
    r"|section\s+[A-Z](?:\s+[—-]\s+[^\n]{1,120})?"
    r"|article\s+\d+[A-Za-z]?"
    r"|annex\s+[A-Z0-9IVXLC]+"
    r"|recital\s+\d+[A-Za-z]?"
    r")(?=[A-Z]|\s|$)"
)


def load_pdf(path: str | Path) -> list[PageText]:
    pages, _ = load_pdf_with_metadata(path)
    return pages


def load_pdf_with_metadata(path: str | Path) -> tuple[list[PageText], dict]:
    with Path(path).open("rb") as handle:
        return load_pdf_bytes_with_metadata(handle.read())


def load_pdf_bytes(file_bytes: bytes) -> list[PageText]:
    pages, _ = load_pdf_bytes_with_metadata(file_bytes)
    return pages


def load_pdf_bytes_with_metadata(file_bytes: bytes) -> tuple[list[PageText], dict]:
    reader = PdfReader(BytesIO(file_bytes))
    metadata = _normalize_metadata(reader.metadata)
    pages: list[PageText] = []

    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").replace("\r\n", "\n").strip()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        pages.append(PageText(page_number=index, text=text, heading_hints=_extract_heading_hints(text, lines)))

    return pages, metadata


def _extract_heading_hints(text: str, lines: list[str]) -> list[str]:
    hints: list[str] = []
    for line in lines[:12]:
        hints.extend(_extract_structural_headings(line))

        normalized = line.strip()
        if normalized and _looks_like_heading(normalized):
            hints.append(normalized)

    if not hints:
        hints.extend(_extract_structural_headings(text[:2000]))

    seen: set[str] = set()
    ordered: list[str] = []
    for hint in hints:
        normalized_hint = " ".join(hint.split())
        if not normalized_hint or normalized_hint in seen:
            continue
        seen.add(normalized_hint)
        ordered.append(normalized_hint)
    return ordered


def _extract_structural_headings(text: str) -> list[str]:
    headings: list[str] = []
    for match in STRUCTURAL_HEADING_RE.finditer(text):
        heading = " ".join(match.group(1).split())
        if heading:
            headings.append(heading)
    return headings


def _looks_like_heading(text: str) -> bool:
    prefixes = ("title", "chapter", "section", "article", "annex", "recital")
    lowered = text.lower()
    if lowered.startswith(prefixes) and len(text) <= 240:
        return True

    alpha = "".join(char for char in text if char.isalpha())
    return bool(alpha) and len(text) <= 80 and len(text.split()) <= 12 and text == text.upper()


def _normalize_metadata(metadata: dict | None) -> dict:
    if not metadata:
        return {}
    normalized: dict[str, str] = {}
    for key, value in metadata.items():
        if key is None or value is None:
            continue
        normalized[str(key).lstrip("/")] = str(value)
    return normalized
