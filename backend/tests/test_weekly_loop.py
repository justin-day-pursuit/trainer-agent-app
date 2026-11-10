"""
End-to-end test of the weekly loop against a temporary in-memory database:
client logs -> draft appears for the trainer -> trainer edits and approves -> client sees it.
"""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.auth import get_current_client_session, get_current_trainer
from app.core.database import Base, get_db
from app.main import app
from app.models.client import ClientProfile
from app.models.trainer import Trainer
from app.models.workout import WorkoutPlan

PLAN = [
    {"exercise_id": "ex_bench", "name": "Bench", "sets": 3, "target_reps": 10, "target_weight_lbs": 135.0},
    {"exercise_id": "ex_squat", "name": "Squat", "sets": 3, "target_reps": 12, "target_weight_lbs": 185.0},
]


@pytest.fixture
def api():
    import asyncio

    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with factory() as db:
            for sub, email, name in [("me", "me@example.com", "Sarah"), ("other", "o@example.com", "Other Client")]:
                trainer = Trainer(supabase_user_id=sub, email=email, full_name=sub)
                db.add(trainer)
                await db.flush()
                client = ClientProfile(trainer_id=trainer.id, full_name=name)
                db.add(client)
                await db.flush()
                db.add(WorkoutPlan(client_id=client.id, week_label="Week 1 - Base", status="approved", exercises_json=PLAN, safety_flags_json=[]))
            await db.commit()

    asyncio.run(setup())

    async def override_db():
        async with factory() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_trainer] = lambda: {"sub": "me"}
    app.dependency_overrides[get_current_client_session] = lambda: SimpleNamespace(client_id=1)
    yield TestClient(app)
    app.dependency_overrides.clear()


def log_workout(api, request_id="req-1"):
    sets = [
        {"exercise_id": "ex_bench", "set_num": n, "weight_lbs": 135, "reps": 10, "pain_flag": n == 3, "note": "shoulder pinched" if n == 3 else None, "effort": "challenging"}
        for n in (1, 2, 3)
    ] + [
        {"exercise_id": "ex_squat", "set_num": n, "weight_lbs": 185, "reps": 12, "pain_flag": False, "effort": "easy"}
        for n in (1, 2, 3)
    ]
    response = api.post(
        "/api/v1/s/t/log",
        json={"client_request_id": request_id, "raw_input": "x", "confirmed_sets": sets, "has_pain_flag": True, "pain_summary": "Shoulder pinched on the last bench set."},
    )
    assert response.status_code == 201


def only_draft(api):
    plans = api.get("/api/v1/trainer/dashboard").json()["pending_plans"]
    assert len(plans) == 1
    return plans[0]


def test_logging_creates_a_draft_with_reasons_and_a_pain_flag(api):
    log_workout(api)
    draft = only_draft(api)
    bench, squat = draft["exercises"]
    assert (bench["target_reps"], bench["target_weight_lbs"]) == (10, 135.0)
    assert (squat["target_reps"], squat["target_weight_lbs"]) == (8, 190.0)
    assert "5 lbs" in squat["reason"]
    assert draft["overall_effort"] == "challenging"
    assert draft["safety_flags"][0]["message"].startswith("[Pain Reported]")
    assert draft["week_label"].startswith("Week 2")


def test_a_new_log_replaces_the_earlier_draft(api):
    log_workout(api, "req-1")
    log_workout(api, "req-2")
    only_draft(api)


def test_client_keeps_old_plan_until_trainer_approves_then_sees_the_edit(api):
    log_workout(api)
    draft = only_draft(api)
    assert api.get("/api/v1/s/t").json()["active_plan"]["week_label"].startswith("Week 1")

    edit = api.put(
        f"/api/v1/trainer/plans/{draft['id']}",
        json={"exercises": [{"exercise_id": "ex_bench", "target_reps": 9, "target_weight_lbs": 130}]},
    )
    assert edit.status_code == 200
    assert api.post(f"/api/v1/trainer/plans/{draft['id']}/approve").status_code == 200

    plan = api.get("/api/v1/s/t").json()["active_plan"]
    assert plan["week_label"].startswith("Week 2")
    assert (plan["exercises"][0]["target_reps"], plan["exercises"][0]["target_weight_lbs"]) == (9, 130)
    assert api.get("/api/v1/trainer/dashboard").json()["pending_plans"] == []
    assert api.post(f"/api/v1/trainer/plans/{draft['id']}/approve").status_code == 409


def test_a_trainer_cannot_see_or_approve_another_trainers_plan(api):
    log_workout(api)
    draft = only_draft(api)
    app.dependency_overrides[get_current_trainer] = lambda: {"sub": "other"}
    assert api.get("/api/v1/trainer/dashboard").json()["pending_plans"] == []
    assert api.post(f"/api/v1/trainer/plans/{draft['id']}/approve").status_code == 404


def test_new_client_starts_with_a_live_plan_and_private_link(api):
    response = api.post(
        "/api/v1/trainer/clients",
        json={
            "full_name": " Dana Lee ",
            "injuries": ["left knee", " "],
            "exercises": [
                {"name": "Goblet Squat", "sets": 3, "target_reps": 8, "target_weight_lbs": 40},
                {"name": "Goblet Squat", "sets": 2, "target_reps": 10},
            ],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["full_name"] == "Dana Lee"
    assert len(body["session_token"]) == 36

    app.dependency_overrides[get_current_client_session] = lambda: SimpleNamespace(client_id=body["client_id"])
    plan = api.get("/api/v1/s/any").json()["active_plan"]
    ids = [row["exercise_id"] for row in plan["exercises"]]
    assert ids[0] == "ex_goblet_squat"
    assert len(set(ids)) == 2


def test_new_client_needs_at_least_one_exercise(api):
    response = api.post("/api/v1/trainer/clients", json={"full_name": "Dana", "exercises": []})
    assert response.status_code == 422


def easy_sets(reps=10):
    return [
        {"exercise_id": exercise_id, "set_num": n, "weight_lbs": 100, "reps": target, "pain_flag": False, "effort": "easy"}
        for exercise_id, target in (("ex_bench", 10), ("ex_squat", 12))
        for n in (1, 2, 3)
    ]


def log_easy_workout(api):
    assert api.post(
        "/api/v1/s/t/log",
        json={"client_request_id": "easy-1", "raw_input": "x", "confirmed_sets": easy_sets(), "has_pain_flag": False},
    ).status_code == 201


def test_logging_locks_the_link_until_the_trainer_approves(api):
    assert api.get("/api/v1/s/t").json()["link_status"] == "active"
    log_easy_workout(api)
    view = api.get("/api/v1/s/t").json()
    assert view["link_status"] == "pending_review"
    assert len(view["last_session"]["sets"]) == 6
    draft = only_draft(api)
    assert draft["status"] == "pending_approval"
    api.post(f"/api/v1/trainer/plans/{draft['id']}/approve")
    view = api.get("/api/v1/s/t").json()
    assert view["link_status"] == "active"
    assert view["last_session"] is None


def test_routine_draft_goes_to_auto_approve_and_can_be_bulk_approved(api):
    log_easy_workout(api)
    draft = only_draft(api)
    assert draft["review_group"] == "auto_approve"
    assert draft["badges"] == []
    result = api.post("/api/v1/trainer/plans/approve-batch", json={"plan_ids": [draft["id"]]}).json()
    assert result == {"approved_plan_ids": [draft["id"]], "skipped_plan_ids": []}
    assert api.get("/api/v1/s/t").json()["active_plan"]["week_label"].startswith("Week 2")


def test_pain_or_stalled_drafts_need_review_and_bulk_approve_refuses_them(api):
    log_workout(api)
    draft = only_draft(api)
    assert draft["review_group"] == "attention_required"
    assert set(draft["badges"]) == {"Pain Reported", "Stalled Progression"}
    result = api.post("/api/v1/trainer/plans/approve-batch", json={"plan_ids": [draft["id"]]}).json()
    assert result == {"approved_plan_ids": [], "skipped_plan_ids": [draft["id"]]}
    assert api.get("/api/v1/s/t").json()["link_status"] == "pending_review"


def test_bulk_approve_cannot_touch_another_trainers_draft(api):
    log_easy_workout(api)
    draft = only_draft(api)
    app.dependency_overrides[get_current_trainer] = lambda: {"sub": "other"}
    result = api.post("/api/v1/trainer/plans/approve-batch", json={"plan_ids": [draft["id"]]}).json()
    assert result["approved_plan_ids"] == []


# --- Wave 3: triage, roster, and client links ---


@pytest.fixture
def stand_in_assistant(monkeypatch):
    from unittest.mock import AsyncMock

    from app.services import triage_service

    draft = AsyncMock(return_value="Hey, checking in!")
    monkeypatch.setattr(triage_service.assistant, "draft_checkin_message", draft)
    return draft


@pytest.mark.parametrize(
    "days, pain, expected",
    [(0, False, "routine"), (4, False, "routine"), (5, False, "medium"), (7, False, "medium"), (8, False, "high"), (0, True, "high")],
)
def test_urgency_is_decided_in_code(days, pain, expected):
    from app.services.triage_service import compute_urgency

    assert compute_urgency(days, pain) == expected


def test_active_client_is_on_the_roster_but_not_in_triage(api, stand_in_assistant):
    body = api.get("/api/v1/trainer/triage").json()
    assert body["triage_cards"] == []
    assert body["roster"][0]["urgency"] == "routine"
    stand_in_assistant.assert_not_awaited()


def test_pain_raises_a_high_card_and_the_draft_is_saved(api, stand_in_assistant):
    log_workout(api)
    card = api.get("/api/v1/trainer/triage").json()["triage_cards"][0]
    assert card["urgency"] == "high"
    assert card["draft_message"] == "Hey, checking in!"
    assert stand_in_assistant.await_args.kwargs["pain_note"] == "Shoulder pinched on the last bench set."
    api.get("/api/v1/trainer/triage")
    assert stand_in_assistant.await_count == 1


def test_dismissed_card_stays_gone_until_something_new_happens(api, stand_in_assistant):
    log_workout(api, "req-1")
    card = api.get("/api/v1/trainer/triage").json()["triage_cards"][0]
    assert api.post(f"/api/v1/trainer/triage/{card['id']}/dismiss").status_code == 200
    assert api.get("/api/v1/trainer/triage").json()["triage_cards"] == []
    log_workout(api, "req-2")
    assert len(api.get("/api/v1/trainer/triage").json()["triage_cards"]) == 1


def test_trainer_cannot_see_or_dismiss_another_trainers_alert(api, stand_in_assistant):
    log_workout(api)
    card = api.get("/api/v1/trainer/triage").json()["triage_cards"][0]
    app.dependency_overrides[get_current_trainer] = lambda: {"sub": "other"}
    body = api.get("/api/v1/trainer/triage").json()
    assert body["triage_cards"] == []
    assert [row["full_name"] for row in body["roster"]] == ["Other Client"]
    assert api.post(f"/api/v1/trainer/triage/{card['id']}/dismiss").status_code == 404


def test_new_link_replaces_the_old_one_and_only_for_your_own_clients(api, stand_in_assistant):
    first = api.post("/api/v1/clients/1/sessions").json()["session_token"]
    second = api.post("/api/v1/clients/1/sessions").json()["session_token"]
    assert first != second
    assert api.get("/api/v1/trainer/triage").json()["roster"][0]["session_token"] == second
    assert api.post("/api/v1/clients/2/sessions").status_code == 404


def test_clients_list_only_shows_your_own(api):
    names = [client["full_name"] for client in api.get("/api/v1/clients").json()]
    assert names == ["Sarah"]
