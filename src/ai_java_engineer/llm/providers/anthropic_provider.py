"""Anthropic Claude API Provider using HTTPX."""

import json
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from ai_java_engineer.infrastructure.errors import PlatformError
from ai_java_engineer.llm.base import ModelProvider, ModelRequest, ModelResponse, TokenUsage

T = TypeVar("T", bound=BaseModel)


class AnthropicProvider(ModelProvider):
    """Anthropic Claude model provider."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "claude-3-5-sonnet-20240620",
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.endpoint = "https://api.anthropic.com/v1/messages"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate(self, request: ModelRequest) -> ModelResponse:
        start_time = time.time()
        payload = {
            "model": self.model_name,
            "max_tokens": request.max_tokens or 4096,
            "messages": [{"role": "user", "content": request.prompt}],
            "temperature": request.temperature,
        }
        if request.system_instruction:
            payload["system"] = request.system_instruction

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(self.endpoint, json=payload, headers=headers)
            if resp.status_code != 200:
                raise PlatformError(f"Anthropic API error ({resp.status_code}): {resp.text}", code="E303")
            data = resp.json()

        latency_ms = int((time.time() - start_time) * 1000)
        content = data["content"][0]["text"]
        usage_meta = data.get("usage", {})
        prompt_tokens = usage_meta.get("input_tokens", 0)
        completion_tokens = usage_meta.get("output_tokens", 0)

        return ModelResponse(
            content=content,
            raw_response=data,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                estimated_cost_usd=((prompt_tokens * 3.0) + (completion_tokens * 15.0)) / 1_000_000,
            ),
            latency_ms=latency_ms,
        )

    async def generate_structured(
        self, request: ModelRequest, response_model: type[T]
    ) -> tuple[T, ModelResponse]:
        schema = response_model.model_json_schema()
        structured_prompt = (
            f"{request.prompt}\n\n"
            f"Respond with a single JSON object strictly matching this schema:\n"
            f"{json.dumps(schema, indent=2)}"
        )
        req_copy = request.model_copy(update={"prompt": structured_prompt})
        response = await self.generate(req_copy)
        clean_json = response.content.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.startswith("```"):
            clean_json = clean_json[3:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]
        clean_json = clean_json.strip()

        parsed = response_model.model_validate_json(clean_json)
        return parsed, response
