# SPEC-018: Evaluation Framework

## Objective
Establish a scientific, reproducible benchmarking and evaluation framework capable of running standardized test datasets, evaluating visible and hidden test suites, measuring ablation impacts, and categorizing failures via an explicit error taxonomy.

## Context
"I ran it on a ticket and it worked" is not an engineering evaluation. A research-grade AI lab requires reproducible benchmarks, held-out hidden evaluation tests to detect overfitting, and ablation testing to quantify each component's contribution.

## Scope
- Benchmark harness (`BenchmarkRunner`) loading JSONL task datasets.
- Evaluation metrics calculator: Build Success Rate, Visible Test Pass Rate, Hidden Test Pass Rate, Regression Rate, Cost per Task.
- Error taxonomy: `E001` (Requirement Misunderstanding) to `E010` (Hallucinated Dependency).
- Ablation testing framework comparing system configurations (e.g. Coder Only vs Full Platform).

## Non-scope
- Subjective human sentiment surveys.

## Functional Requirements
- FR-18.1: Load task specifications with visible tests and hidden evaluation tests.
- FR-18.2: Compute pass rates without leaking hidden test source code to the agent prompts.
- FR-18.3: Categorize any failure against the standardized taxonomy codes.
- FR-18.4: Generate an evaluation report comparing baseline vs agent performance.

## Error Taxonomy
- `E001`: Requirement misunderstanding
- `E002`: Architecture violation
- `E003`: Compilation failure
- `E004`: Functional test failure
- `E005`: Test generation failure
- `E006`: Regression on existing codebase
- `E007`: Security policy violation
- `E008`: Context retrieval failure
- `E009`: Tool execution error
- `E010`: Hallucinated dependency

## Schemas
```python
class BenchmarkTask(BaseModel):
    task_id: str
    title: str
    requirement: str
    repository_seed: str
    visible_tests: list[str]
    hidden_tests: list[str]
    expected_files: list[str]

class BenchmarkReport(BaseModel):
    total_tasks: int
    build_success_rate: float
    visible_pass_rate: float
    hidden_pass_rate: float
    average_cost_usd: float
    average_duration_seconds: float
    error_breakdown: dict[str, int]
```

## Security Considerations
Hidden evaluation tests must be stored in protected namespaces and never injected into the context window.

## Observability
Logs per-task metrics, ablation delta comparisons, and summary distributions.

## Failure Handling
Individual task timeouts or failures are caught and classified without stopping the batch.

## Acceptance Criteria
- Benchmark runner executes multi-task datasets, executes hidden tests, and emits a structured report.

## Tests
- `test_benchmark_runner_execution`
- `test_error_taxonomy_classification`
- `test_hidden_test_isolation`

## Definition of Done
Evaluation framework fully functional, tested, and ready to benchmark AI Java engineering tasks.
