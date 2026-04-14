from __future__ import annotations

from docintel.services.ingestion.chunker import chunk_pages
from docintel.services.ingestion.pdf_loader import PageText


def test_chunker():
    pages = [
        PageText(
            page_number=1,
            text="TITLE I\n\nAlpha beta gamma delta.\n\nArticle 1\n\nEpsilon zeta eta theta.",
            heading_hints=["TITLE I", "Article 1"],
        ),
        PageText(
            page_number=2,
            text="Article 2\n\nIota kappa lambda mu.\n\nNu xi omicron pi.",
            heading_hints=["Article 2"],
        ),
        PageText(
            page_number=3,
            text="CHAPTER II\n\nRho sigma tau upsilon.\n\nArticle 3\n\nPhi chi psi omega.",
            heading_hints=["CHAPTER II", "Article 3"],
        ),
    ]

    chunks = chunk_pages(pages, target_tokens=12, overlap_tokens=0)

    assert len(chunks) == 4
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 1
    assert chunks[0].section_path == "TITLE I > Article 1"
    assert chunks[-1].page_start == 3
    assert chunks[-1].section_path == "TITLE I > CHAPTER II > Article 3"


def test_chunker_splits_long_single_block_pages_using_heading_hints():
    pages = [
        PageText(
            page_number=1,
            text="ANNEX V\n" + "This annex requirement sentence. " * 120,
            heading_hints=["ANNEX V"],
        )
    ]

    chunks = chunk_pages(pages, target_tokens=64, overlap_tokens=0)

    assert len(chunks) > 1
    assert all(chunk.section_path == "ANNEX V" for chunk in chunks)
    assert all(chunk.token_count <= 64 for chunk in chunks)
