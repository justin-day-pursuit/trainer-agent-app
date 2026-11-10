"""
PRD Evaluation Cards Test Suite (Task 1.7).

This module validates the 3 core PRD Evaluation Cards for the Workout Logger agent:
1. Case 1 (Golden Normal): Client logs a clean workout (e.g. 3x10 @ 135 lbs, no pain).
2. Case 2 (Golden Edge Case): Client logs mixed exercises with an injury/pain note on the last set
   (e.g. squats easy, bench set 3 was only 8 reps due to pinching).
3. Case 3 (Adversarial): Client submits non-workout chat (e.g. "I hate Mondays. When is the gym closing?").

Includes two modes:
- Deterministic (Mocked): Default fast hermetic tests that verify harness parsing, schema validation,
  and pain scoping without external network calls.
- Live API (@pytest.mark.optional_live): Live end-to-end integration tests that call Claude
  (claude-sonnet-5-5) via the Anthropic API to confirm real-world reasoning and extraction behavior.
"""

import os
from unittest.mock import AsyncMock
import pytest

from app.agents.intake_agent import (
    WorkoutExtraction,
    WorkoutLoggerAgent,
    WorkoutLoggerUnavailable,
)
from app.core.config import get_settings
from app.schemas.workout import ExtractedSet


# Canonical workout plan used across PRD eval card testing
EVAL_PLAN = [
    {
        "exercise_id": "ex_squat",
        "name": "Back Squat",
        "sets": 3,
        "target_reps": 10,
        "target_weight_lbs": 185.0,
    },
    {
        "exercise_id": "ex_bench",
        "name": "Barbell Bench Press",
        "sets": 3,
        "target_reps": 10,
        "target_weight_lbs": 135.0,
    },
]


def helper_agent_with_mock(*answers: WorkoutExtraction) -> WorkoutLoggerAgent:
    """
    Creates a WorkoutLoggerAgent whose internal model call returns canned extraction objects.
    This lets us test the Python harness rules deterministically without hitting the Claude API.
    """
    agent = WorkoutLoggerAgent()
    agent._request_extraction = AsyncMock(side_effect=list(answers))
    return agent


# ==============================================================================
# 1. Deterministic Mocked Tests (Fast, Hermetic, CI-Safe)
# ==============================================================================


@pytest.mark.asyncio
async def test_eval_card_case_1_golden_normal_mocked():
    """
    Case 1 (Golden Normal - Mocked):
    Verifies that a clean workout log produces structured sets matching prescribed weights
    and reps with no pain flags.
    """
    mock_sets = [
        ExtractedSet(
            exercise_id="ex_bench",
            set_num=i,
            weight_lbs=135.0,
            reps=10,
            pain_flag=False,
            note="Felt good",
        )
        for i in range(1, 4)
    ]
    agent = helper_agent_with_mock(
        WorkoutExtraction(
            status="complete",
            extracted_sets=mock_sets,
            clarifying_question=None,
            pain_summary=None,
        )
    )

    result = await agent.parse_workout_submission(
        "Did bench 135 for 3 sets of 10. Felt good.", EVAL_PLAN
    )

    assert result["status"] == "complete"
    assert len(result["extracted_sets"]) == 3
    assert result["has_pain_flag"] is False
    assert result["pain_summary"] is None
    for s in result["extracted_sets"]:
        assert s.exercise_id == "ex_bench"
        assert s.weight_lbs == 135.0
        assert s.reps == 10
        assert s.pain_flag is False


@pytest.mark.asyncio
async def test_eval_card_case_2_golden_edge_mocked():
    """
    Case 2 (Golden Edge Case - Mocked):
    Verifies that when a client logs two exercises and reports pain on the final set
    of one exercise, the pain flag and note are isolated specifically to that affected set.
    """
    squat_sets = [
        ExtractedSet(
            exercise_id="ex_squat",
            set_num=i,
            weight_lbs=185.0,
            reps=10,
            pain_flag=False,
            effort="easy",
        )
        for i in range(1, 4)
    ]
    bench_sets = [
        ExtractedSet(
            exercise_id="ex_bench",
            set_num=1,
            weight_lbs=135.0,
            reps=10,
            pain_flag=False,
        ),
        ExtractedSet(
            exercise_id="ex_bench",
            set_num=2,
            weight_lbs=135.0,
            reps=10,
            pain_flag=False,
        ),
        ExtractedSet(
            exercise_id="ex_bench",
            set_num=3,
            weight_lbs=135.0,
            reps=8,
            pain_flag=True,
            note="shoulder was pinching on the last set",
        ),
    ]
    agent = helper_agent_with_mock(
        WorkoutExtraction(
            status="complete",
            extracted_sets=squat_sets + bench_sets,
            pain_summary="Shoulder pinching reported on last set of bench.",
        )
    )

    result = await agent.parse_workout_submission(
        "Squats were easy did em all. Bench my shoulder was pinching on the last set so I only got 8.",
        EVAL_PLAN,
    )

    assert result["status"] == "complete"
    assert len(result["extracted_sets"]) == 6
    assert result["has_pain_flag"] is True
    assert "pinching" in result["pain_summary"].lower()

    # Confirm pain is isolated only to bench set 3
    bench_last = [
        s for s in result["extracted_sets"]
        if s.exercise_id == "ex_bench" and s.set_num == 3
    ][0]
    assert bench_last.pain_flag is True
    assert bench_last.reps == 8
    assert "pinching" in bench_last.note.lower()

    # Confirm squats remained pain-free
    for s in result["extracted_sets"]:
        if s.exercise_id == "ex_squat":
            assert s.pain_flag is False


@pytest.mark.asyncio
async def test_eval_card_case_3_adversarial_mocked():
    """
    Case 3 (Adversarial Non-Workout - Mocked):
    Verifies that off-topic or conversational chat without workout data returns status="incomplete"
    with zero extracted sets and prompts the client with a clarifying question.
    """
    agent = helper_agent_with_mock(
        WorkoutExtraction(
            status="incomplete",
            extracted_sets=[],
            clarifying_question="Looks like you haven't logged your sets yet. Did you hit the prescribed exercises today?",
            pain_summary=None,
        )
    )

    result = await agent.parse_workout_submission(
        "I hate Mondays. When is the gym closing?", EVAL_PLAN
    )

    assert result["status"] == "incomplete"
    assert result["extracted_sets"] == []
    assert result["clarifying_question"] is not None
    assert result["has_pain_flag"] is False


# ==============================================================================
# 2. Live Claude API Integration Tests (@pytest.mark.optional_live)
# ==============================================================================


@pytest.fixture
def require_anthropic_api():
    """Skips live tests if the Anthropic API key is not configured."""
    settings = get_settings()
    key = settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
    if not key or key.strip() == "" or key.startswith("sk-ant-test"):
        pytest.skip("ANTHROPIC_API_KEY is not configured for live model evaluation.")
    return key


@pytest.mark.optional_live
@pytest.mark.asyncio
async def test_eval_card_case_1_live_claude(require_anthropic_api):
    """
    Live Evaluation - Case 1 (Golden Normal):
    Calls live Claude (claude-sonnet-5-5) with standard workout text.
    Verifies that Claude correctly extracts 3 sets of bench press at 135 lbs for 10 reps
    with no pain flag.
    """
    agent = WorkoutLoggerAgent()
    result = await agent.parse_workout_submission(
        "Did bench 135 for 3 sets of 10. Felt good.", EVAL_PLAN
    )

    assert result["status"] == "complete"
    assert len(result["extracted_sets"]) >= 3

    bench_sets = [s for s in result["extracted_sets"] if s.exercise_id == "ex_bench"]
    assert len(bench_sets) == 3
    for s in bench_sets:
        assert s.reps == 10
        assert s.weight_lbs == 135.0
        assert s.pain_flag is False

    assert result["has_pain_flag"] is False


@pytest.mark.optional_live
@pytest.mark.asyncio
async def test_eval_card_case_2_live_claude(require_anthropic_api):
    """
    Live Evaluation - Case 2 (Golden Edge Case):
    Calls live Claude with a mixed message reporting squats completion and bench pain.
    Verifies that Claude:
    1. Extracts full reps for squats and records effort as easy.
    2. Identifies bench set 3 was reduced to 8 reps.
    3. Accurately sets pain_flag=True only on the affected bench set with a descriptive note.
    4. Generates an accurate pain summary without hallucinating other injuries.
    """
    agent = WorkoutLoggerAgent()
    result = await agent.parse_workout_submission(
        "Squats were easy did em all. Bench my shoulder was pinching on the last set so I only got 8.",
        EVAL_PLAN,
    )

    assert result["status"] == "complete"
    assert result["has_pain_flag"] is True
    assert result["pain_summary"] is not None
    assert "shoulder" in result["pain_summary"].lower() or "pinch" in result["pain_summary"].lower()

    # Verify squats hit prescribed 10 reps and pain_flag is false
    squat_sets = [s for s in result["extracted_sets"] if s.exercise_id == "ex_squat"]
    assert len(squat_sets) == 3
    for s in squat_sets:
        assert s.reps == 10
        assert s.pain_flag is False
        assert s.effort == "easy"

    # Verify bench set 3 was flagged with 8 reps and pain
    bench_sets = [s for s in result["extracted_sets"] if s.exercise_id == "ex_bench"]
    assert len(bench_sets) == 3
    assert bench_sets[0].reps == 10 and bench_sets[0].pain_flag is False
    assert bench_sets[1].reps == 10 and bench_sets[1].pain_flag is False
    assert bench_sets[2].reps == 8
    assert bench_sets[2].pain_flag is True
    assert bench_sets[2].note is not None
    assert "pinch" in bench_sets[2].note.lower() or "shoulder" in bench_sets[2].note.lower()


@pytest.mark.optional_live
@pytest.mark.asyncio
async def test_eval_card_case_3_adversarial_live_claude(require_anthropic_api):
    """
    Live Evaluation - Case 3 (Adversarial Non-Workout Input):
    Calls live Claude with an off-topic question ("I hate Mondays. When is the gym closing?").
    Verifies that Claude:
    1. Does NOT hallucinate workout sets or arbitrarily insert numbers.
    2. Correctly flags status="incomplete".
    3. Returns an empty extracted_sets list.
    4. Formulates a clarifying question asking about today's prescribed exercises.
    """
    agent = WorkoutLoggerAgent()
    result = await agent.parse_workout_submission(
        "I hate Mondays. When is the gym closing?", EVAL_PLAN
    )

    assert result["status"] == "incomplete"
    assert result["extracted_sets"] == []
    assert result["clarifying_question"] is not None
    assert len(result["clarifying_question"]) > 5
    assert result["has_pain_flag"] is False
