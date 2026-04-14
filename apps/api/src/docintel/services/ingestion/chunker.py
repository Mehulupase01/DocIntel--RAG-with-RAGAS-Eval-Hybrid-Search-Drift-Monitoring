from __future__ import annotations

import re
from dataclasses import dataclass

from .pdf_loader import PageText

TOKEN_RE = re.compile(r"\w+|[^\w\s]")
SECTION_PATH_MAX_LEN = 1024


@dataclass(slots=True)
class ChunkDraft:
    text: str
    token_count: int
    char_start: int
    char_end: int
    page_start: int
    page_end: int
    section_path: str | None
    metadata_json: dict


@dataclass(slots=True)
class _Segment:
    text: str
    token_count: int
    char_start: int
    char_end: int
    page_start: int
    page_end: int
    section_path: str | None


def chunk_pages(
    pages: list[PageText],
    target_tokens: int = 512,
    overlap_tokens: int = 64,
) -> list[ChunkDraft]:
    segments = _build_segments(pages, max_segment_tokens=target_tokens)
    if not segments:
        return []

    chunks: list[ChunkDraft] = []
    window: list[_Segment] = []
    current_tokens = 0

    for segment in segments:
        if window and current_tokens + segment.token_count > target_tokens:
            chunks.append(_segments_to_chunk(window))
            window = _tail_overlap(window, overlap_tokens)
            current_tokens = sum(item.token_count for item in window)

        window.append(segment)
        current_tokens += segment.token_count

    if window:
        chunks.append(_segments_to_chunk(window))

    return chunks


def _build_segments(pages: list[PageText], max_segment_tokens: int) -> list[_Segment]:
    segments: list[_Segment] = []
    cursor = 0
    section_stack: list[tuple[int, str]] = []

    for page in pages:
        blocks = [block.strip() for block in re.split(r"\n\s*\n", page.text) if block.strip()]
        if not blocks:
            continue

        if len(blocks) == 1:
            for hint in page.heading_hints:
                if _looks_like_heading(hint):
                    section_stack = _update_section_stack(section_stack, hint)

        for block in blocks:
            normalized = "\n".join(line.strip() for line in block.splitlines() if line.strip())
            if not normalized:
                continue

            heading = _extract_structural_heading(normalized)
            if heading is not None:
                section_stack = _update_section_stack(section_stack, heading)

            block_start = cursor
            block_end = block_start + len(normalized)
            cursor = block_end + 2
            section_path = _serialize_section_stack(section_stack)

            for part_text, part_start, part_end in _split_long_text(normalized, max_segment_tokens):
                segments.append(
                    _Segment(
                        text=part_text,
                        token_count=_estimate_tokens(part_text),
                        char_start=block_start + part_start,
                        char_end=block_start + part_end,
                        page_start=page.page_number,
                        page_end=page.page_number,
                        section_path=section_path,
                    )
                )

    return segments


def _segments_to_chunk(segments: list[_Segment]) -> ChunkDraft:
    text = "\n\n".join(segment.text for segment in segments)
    section_paths = [segment.section_path for segment in segments if segment.section_path]
    unique_section_paths = list(dict.fromkeys(section_paths))
    section_path = _truncate_section_path(unique_section_paths[-1]) if unique_section_paths else None
    return ChunkDraft(
        text=text,
        token_count=sum(segment.token_count for segment in segments),
        char_start=segments[0].char_start,
        char_end=segments[-1].char_end,
        page_start=segments[0].page_start,
        page_end=segments[-1].page_end,
        section_path=section_path,
        metadata_json={
            "section_paths": [_truncate_section_path(path) for path in unique_section_paths],
            "segment_count": len(segments),
        },
    )


def _tail_overlap(segments: list[_Segment], overlap_tokens: int) -> list[_Segment]:
    if overlap_tokens <= 0:
        return []

    overlap: list[_Segment] = []
    token_total = 0
    for segment in reversed(segments):
        if not overlap and segment.token_count > overlap_tokens:
            break
        if overlap and token_total + segment.token_count > overlap_tokens:
            break
        overlap.insert(0, segment)
        token_total += segment.token_count
        if token_total >= overlap_tokens:
            break
    return overlap


def _estimate_tokens(text: str) -> int:
    return max(1, len(TOKEN_RE.findall(text)))


def _split_long_text(text: str, max_tokens: int) -> list[tuple[str, int, int]]:
    matches = list(TOKEN_RE.finditer(text))
    if len(matches) <= max_tokens:
        return [(text, 0, len(text))]

    parts: list[tuple[str, int, int]] = []
    token_index = 0

    while token_index < len(matches):
        end_index = min(token_index + max_tokens, len(matches))
        sentence_break = _find_sentence_break(matches, token_index, end_index)
        if sentence_break is not None:
            end_index = sentence_break

        char_start = matches[token_index].start()
        char_end = matches[end_index - 1].end()
        part_text = text[char_start:char_end].strip()
        if part_text:
            relative_start = text.find(part_text, char_start, char_end + 1)
            relative_end = relative_start + len(part_text)
            parts.append((part_text, relative_start, relative_end))
        token_index = end_index

    return parts or [(text, 0, len(text))]


def _find_sentence_break(matches: list[re.Match[str]], start_index: int, end_index: int) -> int | None:
    for index in range(end_index - 1, start_index, -1):
        if matches[index - 1].group(0) in {".", "!", "?", ";", ":"}:
            return index
    return None


def _looks_like_heading(text: str) -> bool:
    lowered = text.lower()
    if lowered.startswith(("title", "chapter", "section", "article", "annex", "recital")) and len(text) <= 240:
        return True

    alpha = "".join(char for char in text if char.isalpha())
    return bool(alpha) and len(text) <= 80 and len(text.split()) <= 12 and text == text.upper()


def _extract_structural_heading(text: str) -> str | None:
    first_line = text.splitlines()[0].strip()
    if _looks_like_heading(first_line):
        return first_line
    return None


def _serialize_section_stack(section_stack: list[tuple[int, str]]) -> str | None:
    if not section_stack:
        return None
    return _truncate_section_path(" > ".join(text for _, text in section_stack))


def _truncate_section_path(section_path: str | None) -> str | None:
    if section_path is None:
        return None
    return section_path[:SECTION_PATH_MAX_LEN]


def _heading_level(heading: str) -> int:
    prefix = heading.split(maxsplit=1)[0].lower()
    level_map = {"title": 1, "chapter": 2, "section": 3, "article": 4, "annex": 1, "recital": 1}
    return level_map.get(prefix, 99)


def _update_section_stack(section_stack: list[tuple[int, str]], heading: str) -> list[tuple[int, str]]:
    level = _heading_level(heading)
    updated = [(existing_level, existing_heading) for existing_level, existing_heading in section_stack if existing_level < level]
    updated.append((level, heading))
    return updated
