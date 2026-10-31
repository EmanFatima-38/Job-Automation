from functools import lru_cache
from typing import TypeVar

import openai
from pydantic import BaseModel, ValidationError

from app.config import get_settings

settings = get_settings()

T = TypeVar("T", bound=BaseModel)


class AIRefusalError(Exception):
    """The model declined to produce a response."""


class AIParseError(Exception):
    """The model response could not be obtained or parsed into the expected schema."""


@lru_cache
def get_client() -> openai.OpenAI:
    return openai.OpenAI(base_url=settings.nvidia_base_url, api_key=settings.nvidia_api_key,
                         timeout=settings.ai_timeout_seconds, max_retries=1)


def parse_structured(
    *,
    model: str,
    system: str,
    user_content: str,
    output_model: type[T],
    max_tokens: int = 4096,
) -> T:
    client = get_client()
    schema = output_model.model_json_schema()

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": output_model.__name__.lower(),
                    "schema": schema,
                    "strict": True,
                },
            },
            max_tokens=max_tokens,
            temperature=0,
            seed=0,
            # This model has hidden "thinking" tokens on by default, which count against
            # max_tokens and can consume the entire budget on longer inputs before any
            # actual output is produced (the root cause behind several truncated/empty
            # response bugs). We want deterministic structured JSON, not reasoning - turn
            # it off so the full budget goes to the actual answer.
            extra_body={"chat_template_kwargs": {"thinking": False}},
        )
    except (openai.APIStatusError, openai.APIConnectionError) as e:
        raise AIParseError(f"NVIDIA API request failed: {e}") from e

    choice = response.choices[0]

    if choice.finish_reason == "content_filter":
        raise AIRefusalError("The model declined to process this request")

    content = choice.message.content
    if not content:
        raise AIParseError("The model returned an empty response")

    try:
        return output_model.model_validate_json(content)
    except ValidationError as e:
        raise AIParseError(f"Model output failed schema validation: {e}") from e


def generate_text(*, model: str, system: str, user_content: str, max_tokens: int = 4096) -> str:
    """Plain, unconstrained text generation - no response_format/json_schema. Strict JSON
    schema mode reliably truncates long free-text output (a cover letter comes back cut off
    after ~60 tokens with finish_reason="stop", even though the exact same prompt without
    response_format produces a complete, well-formed response) - a gateway-level issue with
    constrained decoding on a schema that's essentially one long string field. Use this for
    generation tasks (cover letters, bullet lists) where the output is prose, not multi-field
    structured data."""
    client = get_client()

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            max_tokens=max_tokens,
            temperature=0,
            seed=0,
            extra_body={"chat_template_kwargs": {"thinking": False}},
        )
    except (openai.APIStatusError, openai.APIConnectionError) as e:
        raise AIParseError(f"NVIDIA API request failed: {e}") from e

    choice = response.choices[0]

    if choice.finish_reason == "content_filter":
        raise AIRefusalError("The model declined to process this request")

    content = choice.message.content
    if not content:
        raise AIParseError("The model returned an empty response")

    return content
