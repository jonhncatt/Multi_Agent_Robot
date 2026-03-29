# Swarm MVP Operations

## What This Flow Is For

`research_module` Swarm MVP is the bounded multi-branch research flow.

Its job is narrow:

- split a broad research request into explicit branch inputs
- run each branch through the existing research path
- recover failed branches through `serial_replay`
- merge usable evidence
- mark conflicts instead of forcing arbitration
- return a business-readable result that explains confidence and degradation

It is not supposed to:

- become a kernel-level scheduler
- hide branch failures behind a false “success”
- overrule conflicting evidence
- behave like a smart judge

## Result Grades

### `success`

Use this when:

- the final merge produced at least two usable findings
- no failed branch remains after degradation handling
- no conflict marker remains in the final evidence
- no degraded recovery path was needed

Return strategy:

- `deliver_swarm_summary`

Operational expectation:

- safe to present as the default multi-branch result
- no extra caveat is required beyond the normal summary

### `degraded`

Use this when:

- the final merge is still usable
- but at least one branch needed degraded recovery handling
- and the final evidence does not remain in conflict

Return strategy:

- `return_swarm_summary_with_caveat`

Operational expectation:

- keep the overall result
- explicitly show which branch degraded
- explain why the final result is still usable

### `insufficient_evidence`

Use this when:

- branch evidence remains in conflict
- or the final merge is too thin to support a confident result

Return strategy:

- `report_swarm_unreliable_and_offer_refine_or_escalate`

Operational expectation:

- do not present the output as a confident final answer
- explain the conflict or evidence gap
- suggest refining the request or escalating to a higher-level workflow

### `failed`

Use this when:

- one or more branches still fail after degradation handling
- or no stable final merge can be produced

Return strategy:

- `report_swarm_failure`

Operational expectation:

- fail explicitly
- do not dress this up as degraded success

## What Counts As Operational Success

From an operations point of view, Swarm MVP counts as successful when:

- it returns `success` or `degraded`
- the business output has all three layers:
  - `overall_summary`
  - `per_branch_evidence`
  - `conflict_and_degradation_notes`
- the result clearly explains merge participation, conflict status, and reliability

`insufficient_evidence` is a handled output, not an execution crash, but it is not a confident success state.

## Metrics

Swarm metrics are emitted into `artifacts/platform_metrics/latest.json` under `swarm`.

Track at least:

- `gate_case_count`
- `business_output_present_count`
- `branch_count`
- `merged_finding_count`
- `degraded_run_count`
- `failed_branch_count`
- `conflict_detected_count`
- `result_grade_counts`
- `return_strategy_counts`

Interpretation:

- rising `degraded_run_count` means recovery paths are being used more often
- rising `failed_branch_count` means the flow is no longer holding branch failures inside safe degradation
- rising `conflict_detected_count` means the flow is surfacing disagreement rather than hiding it
- `business_output_present_count` should match `gate_case_count`; if it does not, the business-facing contract has drifted

## When To Escalate

Escalate beyond Swarm MVP when:

- repeated runs stay in `insufficient_evidence`
- conflict needs human arbitration
- the request really requires a broader planner or a richer research workflow

Do not escalate automatically for every `degraded` result. A recovered branch is still an acceptable Swarm outcome when the final merge remains coherent.
