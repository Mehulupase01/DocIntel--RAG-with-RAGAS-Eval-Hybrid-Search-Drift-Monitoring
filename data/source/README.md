# Source Data

## EU AI Act PDF
- Preferred source: an official EUR-Lex, Publications Office, or EU Parliament PDF for the adopted AI Act text
- Intended usage in this repo:
  - pass a local PDF path to `uv run python -m docintel.tools.ingest_eu_ai_act --path "<pdf>"`
  - or set `EU_AI_ACT_PDF_URL` in `.env` for download-driven ingestion
- Verification target for Phase 2: ingest the real EU AI Act PDF end to end and confirm that `chunks` contains rows for the resulting `documents.id`

## Verified Source
- Verified on 2026-04-14 with the official Publications Office download handler URL:
  - `https://op.europa.eu/o/opportal-service/download-handler?format=PDF&identifier=dc8116a1-3fe6-11ef-865a-01aa75ed71a1&language=en&productionSystem=cellar`
- Local ignored verification file:
  - `data/source/eu_ai_act_2024_1689_en.pdf`
- SHA256:
  - `bba630444b3278e881066774002a1d7824308934f49ccfa203e65be43692f55e`
- Verification ingest result:
  - document id `106ea9d5-f534-4620-873f-68ff43cabf72`
  - `144` pages
  - `331` chunks

## Source Note
- Direct EUR-Lex PDF endpoints were returning an AWS WAF challenge from this execution environment on 2026-04-14, so the official Publications Office mirror was used for the verified Phase 2 ingest.
