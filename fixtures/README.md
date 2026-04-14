# Evaluation Fixtures

## Current Suite
- Primary file: `fixtures/eu_ai_act_qa_v1.json`
- Current payload version: `v0.1`
- Current scope: 25 question/answer cases over the official English EU AI Act PDF
- Source PDF sha256: `bba630444b3278e881066774002a1d7824308934f49ccfa203e65be43692f55e`

## Curation Method
- Start from the ingested EU AI Act corpus and identify high-value regulatory topics.
- Draft concise questions that are answerable from the document alone.
- Write a short ground-truth answer that reflects the expected retrieval and answering target.
- Tag each case with expected articles or annexes and a coarse category.
- Keep the fixture under version control so metric drift is attributable to code or model changes.

## Add A Case
- Add the case to `fixtures/eu_ai_act_qa_v1.json`.
- Keep `id` stable and unique.
- Keep `ground_truth` concise and document-grounded.
- Add at least one expected article or annex reference.
- Validate the file against `fixtures/eu_ai_act_qa_v1.schema.json`.

## Roadmap
- `v0.1` ships 25 cases to unblock the evaluation harness.
- Follow-up expansion target: 100 curated cases for `v1.0`.
