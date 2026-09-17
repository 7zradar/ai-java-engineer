"""Corporate Knowledge Store for company standards, guidelines, and ADR patterns."""

from pydantic import BaseModel, Field


class KnowledgeDocument(BaseModel):
    id: str
    title: str
    tags: list[str] = Field(default_factory=list)
    content: str


class CorporateKnowledgeStore:
    """Stores and retrieves organization-specific engineering guidelines."""

    def __init__(self):
        self.documents: list[KnowledgeDocument] = []
        self._load_defaults()

    def _load_defaults(self) -> None:
        self.documents = [
            KnowledgeDocument(
                id="CORP-SEC-01",
                title="Spring Boot Security Guidelines",
                tags=["security", "spring-boot", "auth"],
                content="All endpoints under /api/v1/ must be authenticated. Never disable CSRF unless JWT stateless filter is registered.",
            ),
            KnowledgeDocument(
                id="CORP-JPA-02",
                title="Data Persistence Standards",
                tags=["jpa", "database", "spring-data"],
                content="Use derived query methods or @Query with named parameters. Never concatenate strings into JPQL queries.",
            ),
            KnowledgeDocument(
                id="CORP-REST-03",
                title="REST API Error Format",
                tags=["rest", "dto", "controller"],
                content="All API errors must return ErrorResponseDTO containing timestamp, status, error, and path.",
            ),
        ]

    def find_relevant(self, query_tags: list[str]) -> list[KnowledgeDocument]:
        """Returns documents that match any of the provided tags."""
        matched = []
        q_lower = {t.lower() for t in query_tags}
        for doc in self.documents:
            doc_tags = {t.lower() for t in doc.tags}
            if q_lower.intersection(doc_tags):
                matched.append(doc)
        return matched
