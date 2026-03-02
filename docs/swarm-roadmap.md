# Swarm Roadmap

## Current State

Current architecture is a backend-orchestrated multi-agent pipeline:

1. Backend orchestrator receives user input
2. `Planner` generates objective, constraints, and plan
3. `Worker` executes the main task and tool loop
4. `Reviewer` checks coverage, risks, and confidence
5. `Revision` optionally rewrites the final answer

This is not a full swarm yet. It is a fixed sequential pipeline with strong observability.

## Why This Is Not Swarm Yet

- Roles are fixed per request
- Execution order is fixed in Python code
- There is no router/coordinator role yet
- No parallel subtask execution
- No dynamic spawning of multiple worker instances
- No result aggregation from multiple concurrent agents

## Direction

Target direction is a lightweight, observable swarm:

- Backend remains the primary orchestrator
- LLM assists with routing decisions
- Subtasks can be split across multiple role instances
- UI keeps showing clear execution flow and role-to-role exchange

## Stage 1: Stabilize The Pipeline

Status: in progress / mostly complete

Goals:

- Keep `Planner -> Worker -> Reviewer -> Revision`
- Make role boundaries explicit
- Make debug flow readable in backend-orchestrator terms
- Make live transparency reliable over SSE
- Keep failures isolated so one role can fail without corrupting the whole request

Exit criteria:

- Team can explain every visible step in the debug panel
- Tool execution traces are readable and attributable to `Worker`
- Reviewer/Revision behavior is predictable on simple tasks

## Stage 2: Add Routing / Triage

Status: next

Introduce a new lightweight role:

- `Router` or `Coordinator`

Responsibilities:

- classify task type
- estimate complexity
- decide whether `Planner` is needed
- decide whether `Reviewer` is needed
- decide whether `Revision` is needed
- decide whether a specialized role should be added

Example structured output:

```json
{
  "task_type": "simple_qa",
  "complexity": "low",
  "use_planner": false,
  "use_worker_tools": false,
  "use_reviewer": false,
  "use_revision": false,
  "specialists": []
}
```

Recommended rules:

- simple knowledge question: `Worker` only
- medium request: `Planner -> Worker`
- tool-heavy request: `Planner -> Worker -> Reviewer`
- high-risk / long-form / customer-facing request: `Planner -> Worker -> Reviewer -> Revision`

Why this stage matters:

- avoids always running four roles
- makes orchestration feel intelligent
- is the first real step toward swarm behavior

## Stage 3: Specialized Roles

Add reusable role templates such as:

- `Researcher`
- `FileReader`
- `Coder`
- `Tester`
- `Fixer`
- `Summarizer`

Important note:

- these are not dynamically invented Python classes
- they are predefined role templates or prompts
- the system dynamically chooses which ones to instantiate

Example:

- `Researcher` gathers web evidence
- `Worker` writes the answer
- `Reviewer` checks consistency with the evidence

## Stage 4: Multi-Instance Execution

Allow multiple instances of the same role:

- `worker_1` reads attachment A
- `worker_2` reads attachment B
- `researcher_1` searches source A
- `researcher_2` searches source B

This is where the system starts feeling like a true swarm.

Required backend abilities:

- subtask IDs
- parent/child task relationships
- shared scratchpad or aggregation context
- result merging
- timeout and retry policy per subtask

## Stage 5: Parallel Branching

Enable parallel execution for independent subtasks.

Examples:

- read attachment and search web at the same time
- run code analysis and test analysis at the same time
- gather multiple source summaries in parallel, then aggregate

Requirements:

- bounded concurrency
- deterministic merge rules
- clear UI for parallel branches
- cost and latency budgeting

## Stage 6: Aggregation Layer

Add explicit aggregation roles or logic:

- `Coordinator` gathers outputs from sub-agents
- resolves contradictions
- chooses the final answer shape
- decides whether another validation pass is needed

This is the point where the system becomes a practical swarm rather than a fixed pipeline.

## Guardrails

Keep these guardrails even when moving toward swarm:

- backend remains source of truth for permissions and tool policy
- not every role gets tool access
- specialized roles should have narrow responsibilities
- every spawned role should be visible in the UI
- every merge decision should be inspectable
- failures should degrade gracefully to a simpler path

## Recommended Near-Term Plan

1. Finish Stage 1 UI and terminology cleanup
2. Implement Stage 2 `Router`
3. Add one specialist role only: `Researcher` or `Fixer`
4. Add multi-instance support only after routing is stable

## Non-Goals Right Now

- fully autonomous open-ended swarm
- self-modifying agent code
- unrestricted dynamic role creation
- hidden orchestration that cannot be inspected
