# Phase 4 — Measurement, Fidelity and Reporting

## Scope and guarantees

The system still registers 48 capabilities; five native coding optimizers are executable. Phase 4 adds a consistent local token-estimate comparison, conservative per-stage evidence-preservation checks, execution duration, feature-level validation results, and explicit metrics provenance. It **does not** add an LLM gateway or provider usage receipts.

Each selected stage is evaluated against its original **authorized, caller-supplied** evidence. For diffs, changed `+` and `-` lines must be retained. For tests, failure/exception anchors must remain. For errors, exception/causal headings must remain. For targeted code explanations, the named Python function must appear in the candidate. Legacy dependency detection still applies.

Those anchors are a *limited fidelity check*, not a proof of semantic equivalence. Higher-risk transformations may need additional validators, golden test fixtures, and model evaluation.

### Metrics

- `original_estimated_tokens`, `optimized_estimated_tokens`, `estimated_reduction_tokens`: same local heuristic applied to fully composed before/after evidence.
- `estimated_reduction_percent`: calculated only if the optimized candidate is safely returned.
- `fidelity_checks`: per-stage check result, checked/preserved counts, reason; no raw sensitive context.
- `fidelity_status`: `passed`, `rejected`, or `not_evaluated`.
- `execution_duration_ms`: server-side measured duration; not LLM end-to-end latency.
- `provider_usage`, `provider_tokens_saved`: null until independently verified provider data is available.
- `delivery_status=payload_returned_to_client`: only proves the API returned a candidate. It does **not** prove the LLM consumed it.

### Test and reporting endpoints

`POST /v1/optimize` runs selected supported strategies and returns a report. `POST /v1/analyze` reports applicability without executing strategies. `GET /v1/reporting/capabilities` documents measurement limitations. `GET /health` reports phase 4.

### Important limitations

- No real provider calls, model-token receipts, billing API or matched ON/OFF provider trials.
- No persistent report store or multi-tenant identity; do not expose the local API publicly.
- No automatic Codex/Copilot/Claude interception or external Token Optimizer integration.
- Fidelity protects selected syntactic evidence only; it cannot guarantee answer correctness or semantic preservation.

### Acceptance

Run `python -m pytest -q`, then send a large synthetic error/test log through Swagger `POST /v1/optimize`. Check that a real candidate is returned, a reduction is estimated, the fidelity result is `passed`, and provider token savings remain `null`. Try a small nonreducing input and confirm it safely skips with no savings claim.
