# SPEC-005: LangGraph State Machine

## Objective
Implement deterministic orchestration around probabilistic components using a strongly typed state machine with persistent checkpointing.

## Context
Autonomous agents must not decide their own lifecycle transitions arbitrarily. The flow between Product, Architect, Coding, Build, Debug, Security, Review, and PR must follow rigorous deterministic logic.

## Scope
- `EngineeringState` TypedDict & Pydantic sync.
- State graph definition with nodes: `product_node`, `architect_node`, `coder_node`, `build_node`, `debug_node`, `test_node`, `security_node`, `review_node`, `git_pr_node`.
- Conditional routing: `after_build_router`, `after_security_router`.
- SQLite checkpointing for paused state, human approval, and recovery.

## Non-scope
- Distributed cluster workflow orchestration.

## Functional Requirements
- FR-5.1: If `build_result.success == False`, route to `debug_node` if `iteration < max_iterations`, else escalate to `human_escalation`.
- FR-5.2: If `security_result.has_critical == True`, halt progression and mark `SECURITY_BLOCKED`.
- FR-5.3: Persist state transitions to SQLite so runs can be resumed after interruption.

## State Transition Logic
```python
def after_build_router(state: EngineeringState) -> str:
    if state["build_result"] and state["build_result"].success:
        return "run_tests"
    if state["iteration"] >= state["max_iterations"]:
        return "human_escalation"
    return "debug_agent"
```

## Security Considerations
State serializations must not store plain-text secrets in the SQLite database.

## Observability
State transitions record timestamp, duration, node name, and checkpoint ID.

## Failure Handling
Uncaught node exceptions transition state to `FAILED` with captured stacktrace in `ExecutionState`.

## Acceptance Criteria
- Full graph executes deterministically.
- Checkpoints allow resuming an interrupted run at the exact node.

## Tests
- `test_state_graph_compilation`
- `test_deterministic_routing_on_build_failure`
- `test_checkpoint_save_and_resume`

## Definition of Done
LangGraph state graph compiled, validated with deterministic routers and persistence tests.
