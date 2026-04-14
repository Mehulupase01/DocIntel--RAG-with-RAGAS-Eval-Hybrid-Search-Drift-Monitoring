from __future__ import annotations

from docintel.schemas.search import RetrievedChunk

SYSTEM_PROMPT = """You are a regulatory document intelligence assistant for the EU AI Act.
Answer only from the supplied contexts.
Every factual claim must include one or more inline citations in the form [c#N].
Use only citation markers that correspond to the supplied contexts.
If the contexts do not support the answer, say that the provided excerpts are insufficient.
Do not invent legal obligations, article numbers, or annex references."""


def build_answer_prompt(query: str, contexts: list[RetrievedChunk]) -> tuple[str, str, str]:
    if contexts:
        context_blocks = "\n\n".join(_format_context(index, context) for index, context in enumerate(contexts, start=1))
    else:
        context_blocks = "No contexts were retrieved."

    user_prompt = (
        "Question:\n"
        f"{query}\n\n"
        "Retrieved contexts:\n"
        f"{context_blocks}\n\n"
        "Write a concise answer grounded only in the retrieved contexts. "
        "Include inline [c#N] citations immediately after each factual statement."
    )
    prompt_text = f"SYSTEM:\n{SYSTEM_PROMPT}\n\nUSER:\n{user_prompt}"
    return SYSTEM_PROMPT, user_prompt, prompt_text


def _format_context(index: int, context: RetrievedChunk) -> str:
    section = context.section_path or "Unspecified section"
    return (
        f"[c#{index}] {context.document_title} | pages {context.page_start}-{context.page_end} | {section}\n"
        f"{context.text}"
    )
