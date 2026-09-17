# SPEC-008: Repository Context Engine

## Objective
Build a lightweight, hybrid code intelligence and context retrieval engine capable of mapping Java projects, locating symbols, classes, and packages, and building bounded LLM context windows without heavy external vector databases.

## Context
Treating code repositories like flat PDF documents leads to hallucinations and wasted context budgets. A senior AI platform uses structural code awareness (AST/regex, symbol extraction, import graphs) to retrieve relevant files efficiently.

## Scope
- Static Java file parser (regex & structural pattern matching).
- `RepositoryMap`: tree structure, Spring Boot annotations detection (`@RestController`, `@Service`, `@Repository`, `@Entity`).
- Token-bounded `ContextBuilder` assembling relevant files under a strict token ceiling (e.g. 30K - 50K tokens).

## Non-scope
- Heavy distributed vector databases or external embeddings API dependencies.

## Functional Requirements
- FR-8.1: Scan workspace root recursively, filtering out build directories (`target/`, `.git/`, `.idea/`).
- FR-8.2: Extract class names, package declarations, and public methods from `.java` files.
- FR-8.3: Build context strings tagged with `[UNTRUSTED REPOSITORY DATA]` delimiters to prevent injection.

## Schemas
```python
class JavaClassInfo(BaseModel):
    package: str
    class_name: str
    annotations: list[str]
    file_path: str
    methods: list[str]

class RepositoryContext(BaseModel):
    root_path: str
    total_files: int
    java_classes: list[JavaClassInfo]
    pom_files: list[str]
```

## Security Considerations
Wrap retrieved code in non-executable data blocks. Path traversal checks are strictly applied during discovery.

## Observability
Log number of scanned files, retrieved tokens, and context budget utilization percentage.

## Failure Handling
Gracefully ignore binary files and malformed syntax without crashing the scan.

## Acceptance Criteria
- Given a Java repository workspace, produce an accurate `RepositoryContext` within 1 second.

## Tests
- `test_repository_map_scanning`
- `test_context_builder_budget_truncation`

## Definition of Done
Context engine functions locally in pure Python, provides fast symbol search and bounded assembly.
