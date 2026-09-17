# SPEC-016: Git & PR Integration

## Objective
Provide audited, deterministic Git lifecycle operations: creating dedicated feature branches (`feat/ai-...`), committing modified files atomically with conventional commit messages, and generating structured Pull Request descriptions.

## Context
The output of an engineering platform is not a zip archive or terminal dump; it is a clean, reviewable Pull Request submitted to a version control system.

## Scope
- Git operations service in pure Python (`git` subprocess / repository API).
- Branch naming convention: `feat/ai-{task_id}-{slug}`.
- Atomic commit creation with Conventional Commits (`feat(scope): message`).
- PR body generator including summary of changes, test coverage report, and architecture links.

## Non-scope
- Merging to `main` or deploying to production environments.

## Functional Requirements
- FR-16.1: Check out a fresh branch from the base branch before applying any changes.
- FR-16.2: Stage only modified files matching the approved `CodePlan`.
- FR-16.3: Format a comprehensive Markdown PR payload containing user stories, changes, test evidence, and review results.

## Schemas
```python
class PullRequestPayload(BaseModel):
    title: str
    branch: str
    base_branch: str
    body: str
    labels: list[str]
    draft: bool = False
    pr_url: str | None = None
```

## Security Considerations
Never perform force pushes (`git push --force`). Never commit directly to protected branches (`main`, `master`).

## Observability
Record commit hashes, branch names, and PR URLs in the execution state and audit log.

## Failure Handling
Merge conflicts or dirty working tree state abort gracefully before modifying history.

## Acceptance Criteria
- Successfully creates branches, commits, and returns a verified PR payload.

## Tests
- `test_git_branch_creation_and_atomic_commit`
- `test_pull_request_payload_generation`

## Definition of Done
Git service verified with local repository test suite.
