"""
Bedrock API client.

Wraps boto3 Bedrock Runtime with two call modes:
  1. invoke_with_tools() — structured output via tool_use (function calling).
     Used by Stages 1, 3, 4.
  2. invoke_text() — free-form prose output.
     Used by Stage 5.

IMPORTANT: modelId must be the inference profile ID, not the bare model ID.
  Bare ID ("anthropic.claude-sonnet-4-5") causes:
    ValidationException: on-demand throughput isn't supported
  Correct ID format: "ap.anthropic.claude-3-5-sonnet-20241022-v2:0"
  Set BEDROCK_MODEL_ID in .env after running:
    aws bedrock list-inference-profiles --region ap-southeast-1
"""

import json
import logging

import boto3

from config import settings

logger = logging.getLogger(__name__)

_ANTHROPIC_VERSION = "bedrock-2023-05-31"


class BedrockClient:
    """
    Boto3 Bedrock Runtime wrapper for Anthropic Claude models.
    """

    def __init__(self) -> None:
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        self._model_id = settings.bedrock_model_id
        logger.info("BedrockClient initialised with model_id=%s", self._model_id)

    def invoke_with_tools(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict],
        max_tokens: int,
    ) -> dict:
        """
        Call Bedrock with tool_use (function calling) and return the tool input.

        The call uses `tool_choice: {type: "any"}` to force the model to call
        one of the provided tools — guaranteeing a structured response.

        Args:
            system: System prompt string.
            messages: List of {"role": ..., "content": ...} message dicts.
            tools: List of Anthropic tool definition dicts.
            max_tokens: Maximum tokens in the response.

        Returns:
            The tool input dict from the first tool_use block in the response.

        Raises:
            ValueError: If the model does not return a tool_use block.
            RuntimeError: If the Bedrock API call fails.
        """
        body = {
            "anthropic_version": _ANTHROPIC_VERSION,
            "system": system,
            "messages": messages,
            "tools": tools,
            "tool_choice": {"type": "any"},
            "max_tokens": max_tokens,
        }

        try:
            response = self._client.invoke_model(
                modelId=self._model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )
        except Exception as exc:
            logger.exception("Bedrock invoke_model failed: %s", exc)
            raise RuntimeError(f"Bedrock API error: {exc}") from exc

        response_body = json.loads(response["body"].read())
        logger.debug("Bedrock response stop_reason=%s", response_body.get("stop_reason"))

        # Extract tool_use block from content list
        for block in response_body.get("content", []):
            if block.get("type") == "tool_use":
                return block.get("input", {})

        raise ValueError(
            f"Bedrock did not return a tool_use block. "
            f"stop_reason={response_body.get('stop_reason')}. "
            f"content={response_body.get('content')}"
        )

    def invoke_text(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int,
    ) -> str:
        """
        Call Bedrock without tool_use and return the raw text response.

        Used by Stage 5 to generate parent-facing prose.

        Args:
            system: System prompt string.
            messages: List of {"role": ..., "content": ...} message dicts.
            max_tokens: Maximum tokens in the response.

        Returns:
            The concatenated text content from the response.

        Raises:
            RuntimeError: If the Bedrock API call fails.
        """
        body = {
            "anthropic_version": _ANTHROPIC_VERSION,
            "system": system,
            "messages": messages,
            "max_tokens": max_tokens,
        }

        try:
            response = self._client.invoke_model(
                modelId=self._model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )
        except Exception as exc:
            logger.exception("Bedrock invoke_model (text) failed: %s", exc)
            raise RuntimeError(f"Bedrock API error: {exc}") from exc

        response_body = json.loads(response["body"].read())

        text_parts = []
        for block in response_body.get("content", []):
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))

        return "\n".join(text_parts).strip()
