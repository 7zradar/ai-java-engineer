"""Tests for QAAgent subagent and CorporateKnowledgeStore integration."""

import pytest
from ai_java_engineer.agents.qa.qa_agent import QAAgent
from ai_java_engineer.domain.architecture import ArchitectureSpec, EndpointSpec
from ai_java_engineer.domain.artifact import CodePlan, FileAction
from ai_java_engineer.domain.requirement import AcceptanceCriterion, ProductSpec
from ai_java_engineer.llm.providers.mock_provider import MockProvider
from ai_java_engineer.retrieval.knowledge_store import CorporateKnowledgeStore


@pytest.mark.asyncio
async def test_qa_agent_generation():
    provider = MockProvider()
    qa_agent = QAAgent(provider)

    prod = ProductSpec(
        title="Payment API",
        summary="Process credit card payments",
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-1",
                scenario="Valid payment",
                given="A valid token",
                when="POST /api/v1/payments",
                then="Returns 201 Created",
            )
        ],
        edge_cases=["Invalid CVV returns 400 Bad Request"],
    )
    arch = ArchitectureSpec(
        summary="Payment REST endpoint",
        endpoints=[
            EndpointSpec(
                method="POST",
                path="/api/v1/payments",
                status_code=201,
                description="Process payment endpoint",
                response_dto="PaymentResponseDTO",
            )
        ],
    )

    code_plan = CodePlan(
        summary="Payment controller",
        actions=[FileAction(path="src/main/java/PaymentController.java", action="CREATE", content="// code")],
    )

    qa_plan = await qa_agent.execute(prod, arch, code_plan)
    assert qa_plan is not None
    assert len(qa_plan.actions) > 0


def test_corporate_knowledge_store_retrieval():
    store = CorporateKnowledgeStore()
    docs = store.find_relevant(["security", "jpa"])
    assert len(docs) >= 2
    assert any(d.id == "CORP-SEC-01" for d in docs)
    assert any(d.id == "CORP-JPA-02" for d in docs)

    text = store.get_guidelines_text(["rest"])
    assert "CORP-REST-03" in text
    assert "ErrorResponseDTO" in text
