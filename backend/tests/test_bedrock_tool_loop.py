import sys
import os
import json
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from backend.llm.bedrock_client import BedrockClient


@pytest.mark.asyncio
async def test_bedrock_tool_loop_single_turn():
    client = BedrockClient.__new__(BedrockClient)
    client._model_id = "test-model"
    client._client = MagicMock()

    # Mock response with final tool call directly
    mock_body = {
        "content": [
            {
                "type": "tool_use",
                "name": "submit_care_pathway",
                "input": {
                    "urgency_level": "routine",
                    "care_setting": "Home monitoring",
                    "immediate_actions": ["Monitor at home"],
                    "clinical_reasoning": "Stable child",
                    "supporting_guidelines": ["chunk_1"],
                },
            }
        ]
    }
    mock_response = {"body": MagicMock()}
    mock_response["body"].read.return_value = json.dumps(mock_body).encode("utf-8")
    client._client.invoke_model.return_value = mock_response

    res, tool_results = await client.ainvoke_with_tools_loop(
        system="test system",
        messages=[{"role": "user", "content": "hello"}],
        tools=[],
        tool_executors={},
        final_tool_name="submit_care_pathway",
        max_tokens=300,
    )

    assert res["urgency_level"] == "routine"
    assert tool_results == {}


@pytest.mark.asyncio
async def test_bedrock_tool_loop_multi_turn():
    client = BedrockClient.__new__(BedrockClient)
    client._model_id = "test-model"
    client._client = MagicMock()

    # Turn 1 response: calls lookup_openfda
    turn1_body = {
        "content": [
            {
                "type": "tool_use",
                "id": "tool_1",
                "name": "lookup_openfda",
                "input": {"drug_name": "Tylenol"},
            }
        ]
    }
    # Turn 2 response: calls submit_care_pathway
    turn2_body = {
        "content": [
            {
                "type": "tool_use",
                "id": "tool_2",
                "name": "submit_care_pathway",
                "input": {
                    "urgency_level": "soon",
                    "care_setting": "Pediatrician",
                    "immediate_actions": ["Rest"],
                    "clinical_reasoning": "Reasoning with Tylenol data",
                    "supporting_guidelines": ["chunk_1"],
                },
            }
        ]
    }

    mock_resp1 = {"body": MagicMock()}
    mock_resp1["body"].read.return_value = json.dumps(turn1_body).encode("utf-8")

    mock_resp2 = {"body": MagicMock()}
    mock_resp2["body"].read.return_value = json.dumps(turn2_body).encode("utf-8")

    client._client.invoke_model.side_effect = [mock_resp1, mock_resp2]

    async def mock_openfda_executor(drug_name: str):
        return {"drug_name": drug_name, "top_reactions": [{"reaction": "Rash", "count": 5}]}

    res, tool_results = await client.ainvoke_with_tools_loop(
        system="test system",
        messages=[{"role": "user", "content": "I gave Tylenol"}],
        tools=[],
        tool_executors={"lookup_openfda": mock_openfda_executor},
        final_tool_name="submit_care_pathway",
        max_tokens=300,
    )

    assert res["urgency_level"] == "soon"
    assert "lookup_openfda" in tool_results
    assert tool_results["lookup_openfda"]["drug_name"] == "Tylenol"
