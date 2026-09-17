"""Domain models for Java / Spring Boot architecture specifications."""

from typing import Literal

from pydantic import BaseModel, Field


class EndpointSpec(BaseModel):
    """REST endpoint specification."""
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
    path: str
    description: str
    request_dto: str | None = None
    response_dto: str
    status_code: int = 200


class ComponentSpec(BaseModel):
    """Java Spring Boot component specification (Controller, Service, etc.)."""
    package: str
    name: str
    component_type: Literal["CONTROLLER", "SERVICE", "REPOSITORY", "ENTITY", "DTO", "CONFIG"]
    description: str
    dependencies: list[str] = Field(default_factory=list)


class EntitySpec(BaseModel):
    """JPA Entity definition."""
    name: str
    table_name: str
    fields: dict[str, str] = Field(default_factory=dict, description="Field name -> Java type")


class ArchitectureDecision(BaseModel):
    """Architecture Decision Record (ADR)."""
    id: str
    title: str
    context: str
    decision: str
    consequences: str


class ArchitectureSpec(BaseModel):
    """Structured architectural blueprint produced by Architect Agent."""
    summary: str
    packages_to_modify: list[str] = Field(default_factory=list)
    components: list[ComponentSpec] = Field(default_factory=list)
    endpoints: list[EndpointSpec] = Field(default_factory=list)
    entities: list[EntitySpec] = Field(default_factory=list)
    dependencies_needed: list[str] = Field(default_factory=list)
    decisions: list[ArchitectureDecision] = Field(default_factory=list)
