"""Domain models for product requirements and specifications."""

from pydantic import BaseModel, Field


class UserStory(BaseModel):
    """User story following standard agile template."""
    id: str = Field(description="Unique story identifier, e.g. US-001")
    title: str
    as_a: str = Field(description="Role / Actor")
    i_want: str = Field(description="Action / Goal")
    so_that: str = Field(description="Value / Benefit")


class AcceptanceCriterion(BaseModel):
    """Falsifiable acceptance criteria in Given-When-Then format."""
    id: str = Field(description="Criterion ID, e.g. AC-001")
    scenario: str = Field(description="Scenario description")
    given: str = Field(description="Initial context")
    when: str = Field(description="Action triggered")
    then: str = Field(description="Expected outcome")


class RequirementSpec(BaseModel):
    """Raw incoming user feature requirement."""
    id: str
    title: str
    raw_text: str
    target_repository: str
    branch_base: str = "main"
    constraints: list[str] = Field(default_factory=list)
    jira_key: str | None = None
    jira_url: str | None = None


class ProductSpec(BaseModel):
    """Structured product specification produced by Product Agent."""
    title: str
    summary: str
    user_stories: list[UserStory] = Field(default_factory=list)
    acceptance_criteria: list[AcceptanceCriterion] = Field(default_factory=list)
    business_rules: list[str] = Field(default_factory=list)
    edge_cases: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
