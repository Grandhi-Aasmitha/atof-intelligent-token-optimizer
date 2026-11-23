# Phase 3 — Multi-Feature Optimization Orchestration

## Scope

Runs independent evidence optimizers in one deterministic plan. Engine IDs are stable. The planner selects only strategies that have structured caller-provided evidence and an authorized `custom_api`/`return_payload` integration. The feature catalog retains 48 IDs; five native engines remain implemented.

### Ordering, conflicts and limits

1. Error Context (`error_output`)
2. Test Log (`test_output`)
3. Code Diff (`diff`)
4. Code Context (`files`)
5. Repository Retrieval (`files`), mutually exclusive with Code Context

`feature_override` restricts the plan to one **eligible** optimizer and cannot override adapter permissions or missing evidence. `max_optimizers` limits the number of selected strategies, default four. `POST /v1/analyze` runs the planner without executing any engine.

### Safety

Each transformer only receives explicitly supplied evidence; there is no repository file access or background model interception. An unchanged evidence section survives a failed, unsafe or non-reducing stage. Each engine must reduce estimated size both at its own surface and in the composed result. Cross-engine token counts are computed with the same estimator; per-engine savings must **not** be summed. No raw error messages are returned in diagnostics. `payload_returned_to_client` is not proof of LLM consumption.

### Limitations

- External GitHub Token Optimizer remains unconnected pending licensing and a callable integration contract.
- No provider calls or verified model-token savings are claimed.
- This phase does not run dependent cascading transforms of the same source, or dynamically route models.
- The composite artifact is a single string containing explicitly labeled evidence sections; downstream clients must choose whether and how to send it to an LLM.

## Validate

```powershell
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe -m uvicorn atof.api:app --reload --port 8080
```

API: `POST /v1/optimize`, `POST /v1/analyze`, `GET /v1/engines`.
