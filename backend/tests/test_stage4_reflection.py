import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agent.stage4_reflection import Stage4Reflector
from agent.models import CarePathway, UrgencyLevel, ReflectionResult
from common.age_utils import AgeGroup


@pytest.mark.asyncio
async def test_stage4_reflection_complete():
    """Verify Stage4Reflector returns complete verdict when care pathway has no missing info."""
    mock_bedrock = MagicMock()
    mock_bedrock.ainvoke_with_tools = AsyncMock(return_value={
        "is_complete": True,
        "missing_info": "",
        "reason": "Care pathway is well-supported by retrieved guidelines for 6-month-old infant.",
    })

    reflector = Stage4Reflector(bedrock_client=mock_bedrock)

    pathway = CarePathway(
        urgency_level=UrgencyLevel.SOON,
        care_setting="Pediatrician",
        immediate_actions=["Monitor temperature every 4 hours", "Maintain hydration"],
        clinical_reasoning="Fever in 6-month-old without red flags.",
        supporting_guidelines=["NICE_CG160_chunk1"],
    )
    chunks = [{"chunk_id": "c1", "text": "Fever management", "source_authority": "NICE"}]

    result = await reflector.reflect(pathway, chunks, AgeGroup.INFANT)

    assert isinstance(result, ReflectionResult)
    assert result.is_complete is True
    assert result.missing_info == ""
    assert "well-supported" in result.reason
    mock_bedrock.ainvoke_with_tools.assert_called_once()


@pytest.mark.asyncio
async def test_stage4_reflection_incomplete():
    """Verify Stage4Reflector identifies missing info and returns incomplete verdict."""
    mock_bedrock = MagicMock()
    mock_bedrock.ainvoke_with_tools = AsyncMock(return_value={
        "is_complete": False,
        "missing_info": "Need specific guidance on hydration thresholds for infants.",
        "reason": "Hydration guidance missing from primary assessment.",
    })

    reflector = Stage4Reflector(bedrock_client=mock_bedrock)

    pathway = CarePathway(
        urgency_level=UrgencyLevel.SOON,
        care_setting="Pediatrician",
        immediate_actions=["Monitor temperature"],
        clinical_reasoning="Fever assessment incomplete.",
        supporting_guidelines=[],
    )
    chunks = []

    result = await reflector.reflect(pathway, chunks, AgeGroup.INFANT)

    assert isinstance(result, ReflectionResult)
    assert result.is_complete is False
    assert "hydration" in result.missing_info.lower()
    assert result.reason != ""
