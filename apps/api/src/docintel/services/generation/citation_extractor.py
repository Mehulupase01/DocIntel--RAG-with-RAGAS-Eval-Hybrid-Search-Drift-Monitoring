from __future__ import annotations

import re
from dataclasses import dataclass

from docintel.schemas.search import RetrievedChunk

CITATION_PATTERN = re.compile(r"\[c#(\d+)\]")


@dataclass(slots=True)
class ExtractedCitation:
    ordinal: int
    context: RetrievedChunk
    span_text: str


def extract_citations(answer_text: str, contexts: list[RetrievedChunk]) -> tuple[str, list[ExtractedCitation]]:
    citations: list[ExtractedCitation] = []
    next_ordinal = 1
    for match in CITATION_PATTERN.finditer(answer_text):
        marker_index = int(match.group(1)) - 1
        if 0 <= marker_index < len(contexts):
            context = contexts[marker_index]
            citations.append(
                ExtractedCitation(
                    ordinal=next_ordinal,
                    context=context,
                    span_text=context.text,
                )
            )
            next_ordinal += 1

    clean_text = CITATION_PATTERN.sub("", answer_text)
    clean_text = re.sub(r"[ \t]+", " ", clean_text)
    clean_text = re.sub(r"\s+([,.;:?!])", r"\1", clean_text)
    clean_text = re.sub(r"\n{3,}", "\n\n", clean_text)
    return clean_text.strip(), citations
