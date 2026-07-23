import sys
import os
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from agent.tools.openfda_client import OpenFDAClient, DATA_DISCLAIMER


@pytest.mark.asyncio
async def test_openfda_client_success():
    client = OpenFDAClient(timeout=5.0)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {"term": "PYREXIA", "count": 120},
            {"term": "VOMITING", "count": 85},
        ]
    }
    mock_response.raise_for_status = AsyncMock()

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        res = await client.lookup_pediatric_adverse_events("tylenol")

    assert res["drug_name"] == "tylenol"
    assert res["total_pediatric_reports"] == 205
    assert len(res["top_reactions"]) == 2
    assert res["top_reactions"][0] == {"reaction": "PYREXIA", "count": 120}
    assert res["data_disclaimer"] == DATA_DISCLAIMER


@pytest.mark.asyncio
async def test_openfda_client_timeout():
    client = OpenFDAClient(timeout=0.001)

    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Timeout")):
        res = await client.lookup_pediatric_adverse_events("ibuprofen")

    assert res["drug_name"] == "ibuprofen"
    assert "error" in res
    assert "timed out" in res["error"]
    assert res["top_reactions"] == []


@pytest.mark.asyncio
async def test_openfda_client_404_not_found():
    client = OpenFDAClient(timeout=5.0)

    mock_response = AsyncMock()
    mock_response.status_code = 404

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        res = await client.lookup_pediatric_adverse_events("nonexistentmed123")

    assert res["drug_name"] == "nonexistentmed123"
    assert res["total_pediatric_reports"] == 0
    assert res["top_reactions"] == []
    assert "error" not in res
