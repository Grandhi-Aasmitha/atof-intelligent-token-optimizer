# Phase 2 — Central Optimization Engine Integration

Phase 2 adds a shared engine interface and runtime registry. The 48-feature catalog is an inventory, **not** a claim of 48 working implementations. Five native ATOF strategies are executable against caller-supplied evidence: Code Context, Repository Retrieval, Code Diff, Test Log and Error Context.

The external adapter in `src/atof/engines/external.py` intentionally fails closed. No third-party Token Optimizer source is included or executed. Its PolyForm Noncommercial license and stable integration interface require review before commercial integration.

## Flow

1. `POST /v1/analyze` finds features relevant to structured authorized evidence without executing anything.
2. `POST /v1/optimize` chooses **one** supported, eligible strategy (by deterministic priority or an eligible `feature_override`).
3. Engine adapters operate only on data supplied in the request; no automatic source reads, shell commands or model calls occur.
4. A conservative fidelity gate returns a reducing, nonempty candidate; otherwise a safe skip/failure report.
5. Reports state `payload_returned_to_client`, **never verified provider-token savings**.

## Endpoints

- `GET /health`: phase 2
- `GET /v1/features`: all 48 registered IDs; 5 marked implemented
- `GET /v1/engines`: available engine adapters and external integration status
- `POST /v1/analyze`: identify applicable features
- `POST /v1/optimize`: execute one eligible strategy and report result

## Sample repository-retrieval request

```json
{
  "task": "Find invoice total implementation",
  "agent": "custom_api",
  "files": [
    {"path": "invoice.py", "content": "def invoice_total(x): return x * 2\n"},
    {"path": "weather.py", "content": "def forecast(): return 'sunny'\n"}
  ],
  "feature_override": "coding.repository_retrieval",
  "token_budget": 1600
}
```

## Limits

- At most one optimization is executed per call. Multi-feature pipelines are Phase 3.
- Token counts are local estimates, not provider receipts.
- Returned context is not proof the target LLM consumed it.
- Direct agent request transformation remains unsupported for Codex, Copilot and Claude.
- Incremental Context is deferred until verified prior model context can be established.
- Third-party Token Optimizer is not installed or licensed here.

## Validation

`python -m pip install -e ".[dev]"` and `python -m pytest -q`; focused local result: **19 passed** on Python >=3.11.
