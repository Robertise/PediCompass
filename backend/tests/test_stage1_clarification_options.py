import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from agent.stage1_analysis import Stage1Analyzer
from agent.models import QueryAnalysis, AgentResponse


def test_parse_tool_input_with_clarification_options():
    mock_bedrock = MagicMock()
    analyzer = Stage1Analyzer(bedrock_client=mock_bedrock)

    tool_input = {
        "child_age_resolved": True,
        "child_age_days": 60,
        "symptom_summary": "Fever of 38.5C",
        "needs_clarification": True,
        "clarification_questions": ["How long has the fever lasted?"],
        "clarification_options": ["Started today", "1-2 days ago", "More than 3 days"],
    }

    result = analyzer._parse_tool_input(tool_input, child_profile=None)

    assert isinstance(result, QueryAnalysis)
    assert result.needs_clarification is True
    assert result.clarification_questions == ["How long has the fever lasted?"]
    assert result.clarification_options == ["Started today", "1-2 days ago", "More than 3 days"]


def test_parse_tool_input_defensive_sanitization():
    mock_bedrock = MagicMock()
    analyzer = Stage1Analyzer(bedrock_client=mock_bedrock)

    # Test edge cases where Claude returns null or non-list values
    tool_input = {
        "child_age_resolved": "false",
        "child_age_days": "null",
        "symptom_summary": "Unclear symptoms",
        "needs_clarification": "true",
        "clarification_questions": "Not a list",
        "clarification_options": None,
    }

    result = analyzer._parse_tool_input(tool_input, child_profile=None)

    assert result.child_age_resolved is False
    assert result.child_age_days is None
    assert result.needs_clarification is True
    assert result.clarification_questions == []
    assert result.clarification_options == []


@pytest.mark.asyncio
async def test_stage1_analyzer_returns_options():
    mock_bedrock = MagicMock()
    mock_bedrock.ainvoke_with_tools = AsyncMock(return_value={
        "child_age_resolved": False,
        "child_age_days": None,
        "symptom_summary": "Child is coughing",
        "needs_clarification": True,
        "clarification_questions": ["How old is your child?"],
        "clarification_options": ["Under 3 months", "3-12 months", "1-3 years old"],
    })

    analyzer = Stage1Analyzer(bedrock_client=mock_bedrock)
    analysis = await analyzer.analyze(context=[{"role": "user", "content": "My baby is coughing"}])

    assert analysis.child_age_resolved is False
    assert len(analysis.clarification_options) == 3
    assert "Under 3 months" in analysis.clarification_options


def test_parse_tool_input_override_with_attached_child_profile():
    from agent.models import ChildProfile
    from datetime import date, timedelta
    mock_bedrock = MagicMock()
    analyzer = Stage1Analyzer(bedrock_client=mock_bedrock)

    # 300 days old child profile (10 months old)
    dob = (date.today() - timedelta(days=300)).isoformat()
    profile = ChildProfile(
        profile_id="p123",
        nickname="Nam Le",
        dob=dob,
        gender="male",
        weight_kg=9.5,
        medical_conditions=["asthma"],
    )

    # LLM returned false for child_age_resolved because age wasn't in text
    tool_input = {
        "child_age_resolved": False,
        "child_age_days": None,
        "symptom_summary": "Child has a cough",
        "needs_clarification": True,
        "clarification_questions": ["How old is your child?", "When did symptoms start?"],
        "clarification_options": ["Started today", "1-2 days ago"],
    }

    result = analyzer._parse_tool_input(tool_input, child_profile=profile)

    # Profile override MUST set resolved=True and set days=300
    assert result.child_age_resolved is True
    assert result.child_age_days == 300
    # "How old is your child?" MUST be filtered out
    assert result.clarification_questions == ["When did symptoms start?"]

