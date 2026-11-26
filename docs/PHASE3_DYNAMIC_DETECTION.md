# Phase 3 — Dynamic feature detection (revised ten-phase roadmap)

The revised roadmap places dynamic detection in Phase 3, replacing the earlier IntelliJ-first phase numbering. This phase builds on the existing 48-entry catalog and seven executable engines. It does not implement the other 41 or claim native AI interception.

## Flow
~~~mermaid
flowchart TD
 A[Task and authorized structured evidence] --> B[Analyze task and supplied evidence]
 B --> C[Read registered plugin metadata]
 C --> D[Check transport, ON/OFF, applicability, dependency and conflict]
 D --> E[Rank relevant candidates within execution limit]
 E --> F[Execute selected engines and validate fidelity]
 F --> G[Smaller accepted candidate or original fallback]
 G --> H[Applied-only report and single dashboard]
~~~

Task hints describe missing evidence; they do not turn a natural-language question into an actual test log or source file. No filesystem or network reads are performed by the detector. Plugins declare an evidence slot, cardinality, optional task-pattern relevance and optional applicability predicate. Dependencies precede dependents; compatible ready plugins are ranked by task relevance and configured priority. All registered strategies are considered; existing execution limits remain. Unimplemented features stay planned, never executed. The catalog permits more than 48 unique IDs without modifying its loader. The existing evidence slots are unchanged; future provider, memory and conversation operations require their own contracts.

## API and validation
POST /v1/detect: same OptimizeRequest schema, returns intent, supplied/missing evidence, selected feature IDs and decisions. Read-only: no optimizer execution, history or model call. POST /v1/optimize remains the applied-only candidate API. POST /v1/verification/detection runs existing synthetic fixtures without feature_override and compares OFF/ON. This verifies dynamic selection rather than forcing algorithms. Normal dashboard remains report-only; automated checks are optional under Advanced. No raw prompt/history retention or React rewrite in this phase.

~~~powershell
py -3.11 scripts/start_atof.py --verify
~~~
Open the same dashboard, expand Advanced, then Developer diagnostics and click Check automatic feature detection. Results are synthetic, not real provider token savings. Standalone: python -m atof.detection in the installed environment.

Tests include unforced selection across all executable fixtures, task-only negative case, mixed evidence, alternative source strategy, plugin predicate rejection/failure, unsupported agent, OFF/ON, read-only API, and dashboard regression. Existing engine tests and controlled delivery tests remain part of --verify.

## Remaining scope
Phase 4 dashboard enhancements (retain report-only UI; assess requested frontend stack separately), Phase 5 agent adapters, Phase 6 VS Code, Phase 7 JetBrains, Phase 8 browser integration (official supported boundaries only), Phase 9 analytics and comparison, Phase 10 production hardening. Remaining optimizers must be implemented and tested as part of the complete platform. Automatic prompt interception, actual provider savings and broad agent/IDE compatibility remain unverified. Never bypass organization restrictions.
