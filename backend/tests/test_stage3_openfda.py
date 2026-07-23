import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from agent.stage3_reasoning import Stage3Reasoner
from common.age_utils import AgeGroup
from agent.models import UrgencyLevel


@pytest.mark.asyncio
async def test_stage3_reasoner_with_openfda():
    mock_bedrock = MagicMock()
    mock_openfda = MagicMock()

    mock_openfda.lookup_pediatric_adverse_events = AsyncMock(return_value={
        "drug_name": "tylenol",
        "total_pediatric_reports": 50,
        "top_reactions": [{"reaction": "rash", "count": 10}],
        "data_disclaimer": "test disclaimer",
    })

    pathway_output = {
        "urgency_level": "soon",
        "care_setting": "Pediatrician",
        "immediate_actions": ["Rest", "Hydrate"],
        "clinical_reasoning": "Reasoned for 2 year old with fever given Tylenol",
        "supporting_guidelines": ["chunk_1"],
    }
    executed_results = {
        "lookup_openfda": {
            "drug_name": "tylenol",
            "total_pediatric_reports": 50,
            "top_reactions": [{"reaction": "rash", "count": 10}],
            "data_disclaimer": "test disclaimer",
        }
    }

    mock_bedrock.ainvoke_with_tools_loop = AsyncMock(return_value=(pathway_output, executed_results))

    reasoner = Stage3Reasoner(bedrock_client=mock_bedrock, openfda_client=mock_openfda)

    context = [{"role": "user", "content": "My 2 year old has a fever and I gave Tylenol"}]
    chunks = [{"chunk_id": "chunk_1", "text": "Fever management", "source_authority": "AAP"}]

    pathway = await reasoner.reason(context, chunks, AgeGroup.TODDLER)

    assert pathway.urgency_level == UrgencyLevel.SOON
    assert pathway.care_setting == "Pediatrician"
    assert pathway.medication_safety is not None
    assert pathway.medication_safety["drug_name"] == "tylenol"
    assert pathway.medication_safety["total_pediatric_reports"] == 50
