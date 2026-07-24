import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agent.stage5_output import Stage5OutputGenerator, Stage5Output
from agent.models import CarePathway, UrgencyLevel, ReasoningTrace


@pytest.mark.asyncio
async def test_stage5_output_generation():
    """Verify Stage5OutputGenerator produces parent-facing prose and structured sub-sections."""
    mock_bedrock = MagicMock()
    mock_bedrock.ainvoke_text = AsyncMock(return_value=(
        "Based on your 6-month-old's symptoms, a fever without other red flags is generally manageable. "
        "Please schedule a pediatrician visit within 24 hours."
    ))

    generator = Stage5OutputGenerator(bedrock_client=mock_bedrock)

    pathway = CarePathway(
        urgency_level=UrgencyLevel.SOON,
        care_setting="Pediatrician",
        immediate_actions=["Keep child hydrated with breastmilk or formula", "Measure temperature regularly"],
        clinical_reasoning="Fever > 38C in 6-month-old requires routine medical evaluation.",
        supporting_guidelines=["NICE_CG160_chunk1"],
    )
    chunks = [
        {"chunk_id": "c1", "text": "Fever management in under 5s", "source_authority": "NICE"},
        {"chunk_id": "c2", "text": "Hydration guidelines", "source_authority": "WHO"},
    ]
    trace = ReasoningTrace(iterations=1)

    output = await generator.generate(pathway, chunks, trace)

    assert isinstance(output, Stage5Output)
    assert "6-month-old" in output.text
    assert len(output.cited_sources) == 2
    assert output.cited_sources[0]["source_authority"] == "NICE"
    assert output.cited_sources[1]["source_authority"] == "WHO"

    # Pre-visit checklist checks
    assert len(output.pre_visit_checklist) >= 2
    assert any("hydrated" in item.lower() for item in output.pre_visit_checklist)
    assert any("vaccination record" in item.lower() for item in output.pre_visit_checklist)

    # Warning signs checks
    assert len(output.warning_signs) >= 5
    assert any("breathing" in sign.lower() for sign in output.warning_signs)
    mock_bedrock.ainvoke_text.assert_called_once()
