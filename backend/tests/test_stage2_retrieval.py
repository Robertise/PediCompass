import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agent.stage2_retrieval import Stage2Retriever
from common.age_utils import AgeGroup


@pytest.mark.asyncio
async def test_stage2_retrieval_success():
    """Verify Stage2Retriever passes correct age_group filter and returns top 3 reranked chunks."""
    mock_retriever = MagicMock()
    mock_chunks = [
        {"chunk_id": "c1", "text": "Guideline for infant fever", "source_authority": "NICE", "score": 0.85},
        {"chunk_id": "c2", "text": "General fever protocol", "source_authority": "WHO", "score": 0.78},
        {"chunk_id": "c3", "text": "AAP infant guidelines", "source_authority": "AAP", "score": 0.72},
    ]
    mock_retriever.retrieve = AsyncMock(return_value=mock_chunks)

    stage2 = Stage2Retriever(retriever=mock_retriever)

    with patch("agent.stage2_retrieval.embed", return_value=[0.1] * 384):
        results = await stage2.retrieve("High fever in 6 month old", AgeGroup.INFANT)

    assert len(results) == 3
    assert results[0]["chunk_id"] == "c1"
    mock_retriever.retrieve.assert_called_once()
    call_kwargs = mock_retriever.retrieve.call_args.kwargs
    assert call_kwargs["age_group"] == AgeGroup.INFANT
    assert call_kwargs["query_text"] == "High fever in 6 month old"


@pytest.mark.asyncio
async def test_stage2_retrieval_empty_candidates():
    """Verify Stage2Retriever handles empty retrieval results gracefully."""
    mock_retriever = MagicMock()
    mock_retriever.retrieve = AsyncMock(return_value=[])

    stage2 = Stage2Retriever(retriever=mock_retriever)

    with patch("agent.stage2_retrieval.embed", return_value=[0.1] * 384):
        results = await stage2.retrieve("Rare symptom", AgeGroup.NEWBORN)

    assert results == []
    mock_retriever.retrieve.assert_called_once()
