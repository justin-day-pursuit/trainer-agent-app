"""
Schema and Validation Unit Tests.

Verifies that Pydantic models correctly enforce required fields,
types, and error rejection for agent handoffs and set extractions.
"""

import pytest
from pydantic import ValidationError
from app.schemas.agent import AgentHandoff, TriageCard
from app.schemas.workout import ExtractedSet, PrescribedExercise


def test_agent_handoff_schema_valid():
    """
    Ensures that a properly structured agent handoff parses cleanly.
    """
    handoff = AgentHandoff(
        task="Review proposed weights for Week 2",
        context={"client_id": 42, "week": "2026-W45"},
        partial_results={"proposed_weights": {"bench": 140.0}},
        confidence=0.95,
        source_agent="Agent2_ProgressionPlanAgent",
    )
    assert handoff.confidence == 0.95
    assert handoff.context["client_id"] == 42
    assert handoff.source_agent == "Agent2_ProgressionPlanAgent"


def test_agent_handoff_schema_confidence_bounds():
    """
    Ensures that confidence score outside [0.0, 1.0] raises a validation error.
    """
    with pytest.raises(ValidationError):
        AgentHandoff(
            task="Invalid confidence test",
            confidence=1.5,  # Out of bounds (> 1.0)
            source_agent="TestAgent",
        )


def test_extracted_set_validation():
    """
    Ensures that ExtractedSet requires exercise_id, set_num, and reps.
    """
    s = ExtractedSet(
        exercise_id="ex_bench",
        set_num=1,
        reps=10,
        weight_lbs=135.0,
        pain_flag=False,
    )
    assert s.reps == 10
    assert s.weight_lbs == 135.0
    assert not s.pain_flag

    # Missing mandatory reps field should fail
    with pytest.raises(ValidationError):
        ExtractedSet(
            exercise_id="ex_bench",
            set_num=1,
            weight_lbs=135.0,
            # reps omitted!
        )


def test_triage_card_schema():
    """
    Ensures TriageCard structure holds urgency, reason, and optional draft message.
    """
    card = TriageCard(
        client_id=1,
        client_name="Test Client",
        urgency="high",
        reason="Shoulder pinching flagged on set 3",
        recommended_action="Review and modify load",
        draft_message="Hey, how does the shoulder feel today?",
    )
    assert card.urgency == "high"
    assert card.client_id == 1
