# SPEC-019: Corporate Knowledge

## Objective
Provide an optional, modular knowledge ingestion and retrieval layer for organization-specific coding conventions, architectural blueprints, approved library catalogs, and corporate security guidelines.

## Context
Standard LLMs produce generic patterns. Enterprise adoption requires adherence to internal conventions (e.g. customized exception handling, logging standards, approved Spring Boot starters).

## Scope
- Markdown and text guideline ingestion.
- Keyword and tag-based retrieval matching requested features (e.g. "security", "persistence", "rest").
- Integration into the `ContextBuilder` alongside repository code.

## Non-scope
- Multi-gigabyte unstructured document crawler.

## Functional Requirements
- FR-19.1: Ingest documents from a `knowledge/` directory containing corporate standards.
- FR-19.2: Filter and rank standards relevant to the current `ProductSpec` domains.
- FR-19.3: Inject applicable corporate rules into the Architect and Coder prompt context.

## Schemas
```python
class KnowledgeDocument(BaseModel):
    id: str
    title: str
    tags: list[str]
    content: str

class CorporateKnowledgeStore(BaseModel):
    documents: list[KnowledgeDocument] = Field(default_factory=list)
```

## Security Considerations
Ensure corporate knowledge documents do not contain embedded passwords or internal connection strings.

## Observability
Log which corporate standards were injected into the agent prompt context.

## Failure Handling
Missing knowledge store defaults gracefully to base Spring Boot best practices.

## Acceptance Criteria
- Relevant corporate rules are selectively retrieved and injected into architectural planning.

## Tests
- `test_knowledge_store_ingestion_and_tag_retrieval`

## Definition of Done
Knowledge module integrated cleanly as an optional enrichment layer in the pipeline.
