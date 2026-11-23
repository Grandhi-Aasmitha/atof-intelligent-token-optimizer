# Phase 8 — Paired provider observations

The benchmark CLI compares a controlled baseline prompt to the same task with ATOF-optimized evidence. The response returns per-arm reported input/output tokens, cached input where available, response SHA-256, duration and an optional required-term check.

## Free validation

python -m pytest tests/test_phase8.py -q
python -m atof.benchmark_cli --provider synthetic --require-term "Synthetic reply"

Synthetic mode does NOT provide provider usage and must report provider_usage_measured=false and provider_savings_verified=false.

## Real provider tests (explicit paid-call consent)

Set OPENAI_API_KEY or GEMINI_API_KEY securely, then use:

python -m atof.benchmark_cli --provider openai --model YOUR_SUPPORTED_MODEL --accept-paid-calls
python -m atof.benchmark_cli --provider gemini --model YOUR_SUPPORTED_MODEL --accept-paid-calls

The CLI intentionally makes TWO API requests only when --accept-paid-calls is supplied; a nonreducing candidate makes zero calls. Use --order BA to reverse run order and --fixture FILE for a specific synthetic workload. Raw model text is not printed; result includes response hashes.

## Conclusions permitted

Provider usage is an observed receipt for each arm, not proof of causal savings. Compare cached input, model version, correctness and response variability; run repeated matched AB/BA experiments. Lexical required-term checks are not semantic-equivalence proofs. Use only synthetic/non-sensitive input unless permitted to send real data.
