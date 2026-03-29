# Research Module Operations

中文版本: [research_module_operations.zh-CN.md](/Users/dalizhou/Desktop/new_validation_agent/docs/operations/research_module_operations.zh-CN.md)


## What This Module Is For

`research_module` is the second formal business module. Its job is narrow:

- gather sources for a focused research query
- optionally fetch the top source for evidence preview
- return a bounded, explainable summary
- degrade conservatively when evidence is weak or incomplete

It is not supposed to guess, over-arbitrate conflicts, or silently hide degraded evidence quality.

## Result Grades

### `success`

Use this when:

- at least two usable sources were gathered
- no conflicting top-source titles were detected
- no provider fallback was required
- the answer can be returned directly

Return strategy:

- `deliver_answer`

### `degraded`

Use this when:

- the answer is still usable
- but the execution path degraded, for example:
  - top-source fetch failed
  - provider fallback was needed
  - evidence is partially complete but still serviceable

Return strategies:

- `return_search_only_with_caveat`
- `return_answer_with_provider_fallback_note`

Operational expectation:

- do not hide the caveat
- keep the answer, but mark the reliability note clearly

### `insufficient_evidence`

Use this when:

- no usable sources were found
- only one usable source was found
- top sources conflict and the module cannot safely arbitrate

Return strategies:

- `ask_rewrite_query`
- `report_unreliable_and_offer_swarm`

Operational expectation:

- do not present a confident factual answer
- tell the user the evidence is weak or conflicting
- suggest narrowing the query or escalating to Swarm when the topic is broad

### `failed`

Use this when:

- the search step fails before any usable evidence can be gathered
- the tool runtime is unavailable
- every provider path fails and no result can be produced

Return strategy:

- `report_failure`

Operational expectation:

- fail explicitly
- do not mask this as a degraded success

## When The Module Counts As Successful

From an operations point of view, `research_module` counts as successful when:

- it returns `success` or `degraded`
- the returned text clearly matches the evidence quality
- the payload records the result grade, return strategy, and evidence completeness

`insufficient_evidence` is not an execution failure, but it is not a successful evidence answer either. Treat it as a handled but unreliable outcome.

## When To Degrade

Degrade instead of fail when:

- search succeeded but fetch failed
- provider fallback recovered the request
- the module can still return a bounded answer with clear caveats

## When To Ask For Query Rewrite

Ask the user to rewrite or narrow the query when:

- zero usable sources were found
- the request is too broad to produce more than one weak source
- the current wording is likely underspecified

## When To Say “Evidence Is Insufficient / Unreliable”

Say this explicitly when:

- only one usable source was found
- top sources conflict
- the module cannot responsibly collapse disagreement into one answer

## When To Hand Off To Swarm Or Higher-Level Capabilities

Escalate to Swarm or a higher-level research flow when:

- the topic naturally splits into multiple sub-questions
- the single-query path keeps returning `insufficient_evidence`
- conflict needs parallel evidence collection rather than a single-source answer

Do not escalate automatically for every degraded case. Fetch failure or provider fallback alone is not enough reason to invoke Swarm.

## Operational Metrics

The current metrics are emitted into `artifacts/platform_metrics/latest.json` under `research_module`.

Track at least:

- `source_count`
- `fetch_success_rate`
- `evidence_completeness`
- `degraded_response_count`
- `empty_result_count`
- `conflict_detected_count`

Interpretation:

- rising `empty_result_count` means query quality or provider coverage is slipping
- rising `degraded_response_count` means the module is staying alive through fallback or partial evidence more often
- non-zero `conflict_detected_count` means the module is correctly refusing to over-arbitrate conflicting sources
