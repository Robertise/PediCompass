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
import time
from typing import Any, Dict, Optional, Tuple

import boto3
import asyncio

from config import settings

logger = logging.getLogger(__name__)

_ANTHROPIC_VERSION = "bedrock-2023-05-31"


class BedrockClient:
    """
    Boto3 Bedrock Runtime wrapper for Anthropic Claude models.
    """

    def __init__(self) -> None:
        boto_kwargs = {"region_name": settings.aws_region}
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            boto_kwargs["aws_access_key_id"] = settings.aws_access_key_id
            boto_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key

        self._client = boto3.client("bedrock-runtime", **boto_kwargs)
        self._model_id = settings.bedrock_model_id
        logger.info("BedrockClient initialised with model_id=%s", self._model_id)

    def _sanitize_messages(self, messages: list[dict]) -> list[dict]:
        """
        Strip trailing whitespace from assistant messages.
        Anthropic API rejects messages where the final assistant turn 
        ends with whitespace (space, newline, tab).
        """
        sanitized = []
        for msg in messages:
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if isinstance(content, str):
                    msg = {**msg, "content": content.rstrip()}
            sanitized.append(msg)
        return sanitized

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
        messages = self._sanitize_messages(messages)
        body = {
            "anthropic_version": _ANTHROPIC_VERSION,
            "system": system,
            "messages": messages,
            "tools": tools,
            "tool_choice": {"type": "any"},
            "max_tokens": max_tokens,
        }

        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                response = self._client.invoke_model(
                    modelId=self._model_id,
                    body=json.dumps(body),
                    contentType="application/json",
                    accept="application/json",
                )
                break
            except Exception as exc:
                if "ThrottlingException" in str(exc) and attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.warning("Throttled by Bedrock. Retrying in %ds... (attempt %d/%d)", wait_time, attempt + 1, max_retries)
                    time.sleep(wait_time)
                else:
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
        messages = self._sanitize_messages(messages)
        body = {
            "anthropic_version": _ANTHROPIC_VERSION,
            "system": system,
            "messages": messages,
            "max_tokens": max_tokens,
        }

        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                response = self._client.invoke_model(
                    modelId=self._model_id,
                    body=json.dumps(body),
                    contentType="application/json",
                    accept="application/json",
                )
                break
            except Exception as exc:
                if "ThrottlingException" in str(exc) and attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.warning("Throttled by Bedrock (text). Retrying in %ds... (attempt %d/%d)", wait_time, attempt + 1, max_retries)
                    time.sleep(wait_time)
                else:
                    logger.exception("Bedrock invoke_model (text) failed: %s", exc)
                    raise RuntimeError(f"Bedrock API error: {exc}") from exc

        response_body = json.loads(response["body"].read())

        text_parts = []
        for block in response_body.get("content", []):
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))

        return "\n".join(text_parts).strip()

    async def ainvoke_with_tools(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict],
        max_tokens: int,
    ) -> dict:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.invoke_with_tools(system, messages, tools, max_tokens)
        )

    async def ainvoke_text(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int,
    ) -> str:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.invoke_text(system, messages, max_tokens)
        )

    async def ainvoke_with_tools_loop(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict],
        tool_executors: dict[str, Any],
        final_tool_name: str,
        max_tokens: int,
        max_turns: int = 3,
    ) -> tuple[dict, dict[str, Any]]:
        """
        Execute a multi-turn tool_use loop with Bedrock until `final_tool_name` is invoked.

        Args:
            system: System prompt string.
            messages: Conversation history list of message dicts.
            tools: List of Anthropic tool definition dicts.
            tool_executors: Mapping from tool name to async or sync callable.
            final_tool_name: Name of tool that completes the loop (e.g. "submit_care_pathway").
            max_tokens: Max tokens per LLM turn.
            max_turns: Safety cap on turns.

        Returns:
            Tuple of (final_tool_input_dict, executed_tool_results_dict).
        """
        curr_messages = list(messages)
        executed_results: dict[str, Any] = {}
        loop = asyncio.get_running_loop()

        for turn in range(max_turns):
            curr_messages = self._sanitize_messages(curr_messages)
            
            # If intermediate tools executed or on final turn, force final tool name.
            # Otherwise, use {"type": "any"} to guarantee tool execution in every turn.
            if turn == max_turns - 1 or len(executed_results) > 0:
                tool_choice = {"type": "tool", "name": final_tool_name}
            else:
                tool_choice = {"type": "any"}

            body = {
                "anthropic_version": _ANTHROPIC_VERSION,
                "system": system,
                "messages": curr_messages,
                "tools": tools,
                "tool_choice": tool_choice,
                "max_tokens": max_tokens,
            }

            def _invoke():
                max_retries = 3
                for attempt in range(max_retries + 1):
                    try:
                        return self._client.invoke_model(
                            modelId=self._model_id,
                            body=json.dumps(body),
                            contentType="application/json",
                            accept="application/json",
                        )
                    except Exception as exc:
                        if "ThrottlingException" in str(exc) and attempt < max_retries:
                            wait_time = 2 ** attempt
                            logger.warning("Throttled by Bedrock loop. Retrying in %ds... (attempt %d/%d)", wait_time, attempt + 1, max_retries)
                            time.sleep(wait_time)
                        else:
                            raise RuntimeError(f"Bedrock API error: {exc}") from exc

            response = await loop.run_in_executor(None, _invoke)
            response_body = json.loads(response["body"].read())
            content_blocks = response_body.get("content", [])

            # Add assistant response to messages context for multi-turn continuity
            curr_messages.append({"role": "assistant", "content": content_blocks})

            tool_calls = [b for b in content_blocks if b.get("type") == "tool_use"]
            if not tool_calls:
                logger.warning("No tool_use block returned in turn %d (stop_reason=%s). Retrying with forced final tool choice.", turn + 1, response_body.get("stop_reason"))
                body["tool_choice"] = {"type": "tool", "name": final_tool_name}
                response = await loop.run_in_executor(None, _invoke)
                response_body = json.loads(response["body"].read())
                content_blocks = response_body.get("content", [])
                tool_calls = [b for b in content_blocks if b.get("type") == "tool_use"]
                if not tool_calls:
                    raise ValueError(
                        f"Bedrock did not return any tool_use block in loop turn {turn+1}. "
                        f"stop_reason={response_body.get('stop_reason')}"
                    )


            # Check if final tool was called
            for call in tool_calls:
                tool_name = call.get("name")
                if tool_name == final_tool_name:
                    return call.get("input", {}), executed_results

            # Execute intermediate tools
            tool_results_content = []
            for call in tool_calls:
                tool_name = call.get("name")
                tool_use_id = call.get("id")
                tool_input = call.get("input", {})

                if tool_name in tool_executors:
                    logger.info("Executing intermediate tool %r in loop turn %d", tool_name, turn + 1)
                    executor = tool_executors[tool_name]
                    import inspect
                    if inspect.iscoroutinefunction(executor):
                        res = await executor(**tool_input)
                    else:
                        res = await loop.run_in_executor(None, lambda: executor(**tool_input))

                    executed_results[tool_name] = res
                    res_text = json.dumps(res) if not isinstance(res, str) else res
                    tool_results_content.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": res_text,
                    })
                else:
                    logger.warning("Unknown tool %r called in loop turn %d", tool_name, turn + 1)
                    tool_results_content.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": json.dumps({"error": f"Tool {tool_name} not available."}),
                    })

            curr_messages.append({"role": "user", "content": tool_results_content})

        raise RuntimeError(f"Bedrock tool loop exceeded maximum turns ({max_turns}) without invoking {final_tool_name}.")

