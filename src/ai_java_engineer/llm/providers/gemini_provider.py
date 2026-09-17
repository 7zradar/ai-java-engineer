"""Google Gemini API Provider using HTTPX."""

import json
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from ai_java_engineer.infrastructure.errors import PlatformError
from ai_java_engineer.llm.base import ModelProvider, ModelRequest, ModelResponse, TokenUsage

T = TypeVar("T", bound=BaseModel)


class GeminiProvider(ModelProvider):
    """Google Gemini model provider with structured JSON outputs."""

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-pro"):
        self.api_key = api_key
        self.model_name = model_name
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate(self, request: ModelRequest) -> ModelResponse:
        start_time = time.time()
        payload = {
            "contents": [{"parts": [{"text": request.prompt}]}],
            "generationConfig": {
                "temperature": request.temperature,
            },
        }
        if request.system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": request.system_instruction}]}

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(self.endpoint, json=payload)
            if resp.status_code != 200:
                raise PlatformError(f"Gemini API error ({resp.status_code}): {resp.text}", code="E301")
            data = resp.json()

        latency_ms = int((time.time() - start_time) * 1000)
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        usage_meta = data.get("usageMetadata", {})
        prompt_tokens = usage_meta.get("promptTokenCount", 0)
        completion_tokens = usage_meta.get("candidatesTokenCount", 0)

        return ModelResponse(
            content=content,
            raw_response=data,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                estimated_cost_usd=((prompt_tokens * 3.5) + (completion_tokens * 10.5)) / 1_000_000,
            ),
            latency_ms=latency_ms,
        )

    async def generate_structured(
        self, request: ModelRequest, response_model: type[T]
    ) -> tuple[T, ModelResponse]:
        schema = response_model.model_json_schema()
        structured_prompt = (
            f"{request.prompt}\n\n"
            f"CRITICAL: You MUST respond ONLY with a valid JSON object strictly matching this schema:\n"
            f"{json.dumps(schema, indent=2)}\n"
            f"Do not include markdown codeblocks or any leading/trailing text."
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
