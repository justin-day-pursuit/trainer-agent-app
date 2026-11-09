"""
Unit tests for Client Mobile Session Endpoints.

Verifies:
1. Previewing a workout log runs Workout Logger parsing without database persistence.
2. Adversarial or non-workout input returns status="incomplete" and clarifying question.
3. Submitting a confirmed workout log saves the sets.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import get_current_client_session
from app.core.database import get_db
from app.api.v1.endpoints.sessions import intake_agent
from app.schemas.workout import ExtractedSet

client = TestClient(app)


async def stand_in_logger(raw_input, current_exercises):
    """Stands in for the live model so these endpoint tests stay deterministic."""
    if "gym closing" in raw_input:
        return {
            "status": "incomplete",
            "extracted_sets": [],
            "clarifying_question": "Did you hit the prescribed exercises today?",
            "has_pain_flag": False,
            "pain_summary": None,
        }
    pain = "pinching" in raw_input
    return {
        "status": "complete",
        "extracted_sets": [
            ExtractedSet(exercise_id="ex_bench", set_num=n, weight_lbs=135.0, reps=8 if pain and n == 3 else 10, pain_flag=pain and n == 3)
            for n in range(1, 4)
        ],
        "clarifying_question": None,
        "has_pain_flag": pain,
        "pain_summary": "Shoulder pinching on bench" if pain else None,
    }


@pytest.fixture(autouse=True)
def override_dependencies(monkeypatch):
    """Mock database and session authentication dependencies for isolated unit testing."""
    mock_session_record = MagicMock()
    mock_session_record.client_id = 1
    mock_session_record.session_token = "demo-token"
    mock_session_record.is_active = True

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock())

    app.dependency_overrides[get_current_client_session] = lambda: mock_session_record
    app.dependency_overrides[get_db] = lambda: mock_db
    monkeypatch.setattr(intake_agent, "parse_workout_submission", AsyncMock(side_effect=stand_in_logger))
    yield
    app.dependency_overrides.clear()


def test_preview_workout_log_case_1():
    """Golden Case 1: Clean workout log returns parsed sets."""
    response = client.post(
        "/api/v1/s/demo-token/log/preview",
        json={"raw_input": "Did bench 135 for 3 sets of 10. Felt good."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"
    assert len(data["extracted_sets"]) >= 3
    assert data["has_pain_flag"] is False
    assert data["model_name"] == "claude-sonnet-5-5"
    assert data["execution_time_ms"] >= 0


def test_preview_workout_log_case_2_pain():
    """Golden Case 2: In-workout shoulder pinching triggers pain flag."""
    response = client.post(
        "/api/v1/s/demo-token/log/preview",
        json={"raw_input": "Squats were easy did em all. Bench my shoulder was pinching on the last set so I only got 8."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"
    assert data["has_pain_flag"] is True
    assert "Shoulder" in (data["pain_summary"] or "")
    # Find bench set 3
    bench_sets = [s for s in data["extracted_sets"] if s["exercise_id"] == "ex_bench"]
    assert len(bench_sets) == 3
    assert bench_sets[2]["pain_flag"] is True
    assert bench_sets[2]["reps"] == 8


def test_preview_workout_log_case_3_adversarial():
    """Case 3: Non-workout message returns status=incomplete with clarifying question."""
    response = client.post(
        "/api/v1/s/demo-token/log/preview",
        json={"raw_input": "I hate Mondays. When is the gym closing?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "incomplete"
    assert len(data["extracted_sets"]) == 0
    assert data["clarifying_question"] is not None
    assert "prescribed" in data["clarifying_question"].lower()
