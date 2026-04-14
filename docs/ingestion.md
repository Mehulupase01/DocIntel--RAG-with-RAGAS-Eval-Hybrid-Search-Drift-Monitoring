# Ingestion

## Pipeline
1. Read the PDF with `pypdf` and preserve page numbers plus heading hints.
2. Extract structural heading hints (`Title`, `Chapter`, `Section`, `Article`, `Annex`, `Recital`) from the first lines of each page and from flattened `pypdf` text when needed.
3. Split pages into deterministic paragraph-like segments, with an additional long-block fallback that slices dense single-block pages before they exceed the embedding budget.
4. Track heading transitions to build a bounded `section_path` that stays within the DB schema limit.
5. Merge adjacent segments into chunks near the configured token budget.
6. Apply overlap only when the reused tail fits inside the configured overlap budget, so a large segment never balloons the next chunk.
7. Embed every chunk with `BAAI/bge-small-en-v1.5`.
8. Persist the `documents` row, the `chunks` rows, the pgvector embeddings, and the generated `tsvector` column.

## Rationale
- The chunker is deterministic so tests can assert stable chunk counts and ordinal behavior.
- Section-aware chunk metadata makes later citation rendering and retrieval inspection easier.
- The ingestion service stores the original PDF under `ARTIFACT_STORAGE_PATH/documents/` so reingest can reuse the same source bytes after model or chunking changes.
- The embedder normalizes vectors at write time, which keeps cosine retrieval stable for later phases.

## Verified AI Act Ingest
- Official source URL:
  - `https://op.europa.eu/o/opportal-service/download-handler?format=PDF&identifier=dc8116a1-3fe6-11ef-865a-01aa75ed71a1&language=en&productionSystem=cellar`
- SHA256:
  - `bba630444b3278e881066774002a1d7824308934f49ccfa203e65be43692f55e`
- Verified result on 2026-04-14:
  - `144` pages
  - `331` chunks

## Postgres Note
- For larger corpora or slower machines, increase `maintenance_work_mem` before the first heavy pgvector/HNSW build if index creation becomes a bottleneck. The current EU AI Act verification corpus stayed small enough that the default local settings were acceptable.
