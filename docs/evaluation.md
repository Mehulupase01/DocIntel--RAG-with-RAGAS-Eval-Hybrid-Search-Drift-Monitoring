# Evaluation

## Metrics
- `faithfulness`: threshold `0.85`
- `context_precision`: threshold `0.88`
- `context_recall`: threshold `0.80`
- `answer_relevancy`: threshold `0.85`

Per-case pass requires all four metrics to meet or exceed their thresholds.

## Fixture
- File: `fixtures/eu_ai_act_qa_v1.json`
- Schema: `fixtures/eu_ai_act_qa_v1.schema.json`
- Current payload version: `v0.1`
- Current case count: `25`

## Judge Model
- Default judge model: `nvidia/nemotron-3-super-120b-a12b:free`
- Transport: OpenRouter via `OPENROUTER_BASE_URL`

## Commands
- `uv run python -m docintel.tools.run_eval --suite-version v1 --strategy hybrid_reranked`
- `uv run python -m docintel.services.evaluation.ci_gate --fail-on-breach`
