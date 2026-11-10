"""
Checks the planner audit row on the weekly draft.

The engine still decides every weight and rep. These tests use an in-memory
database and a fake planner, so none of them call the network. A real model
call writes one ProgressionPlanner trace. A skip writes nothing. A failed
trace write still saves the draft and the client's log.
"""

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.agents.progression_agent import PlannerFlag, PlannerReview, ProgressionPlannerAgent
from app.core.auth import get_current_client_session, get_current_trainer
from app.core.database import Base, get_db
from app.main import app
from app.models.client import ClientProfile
from app.models.trace import AgentTrace
from app.models.trainer import Trainer
from app.models.workout import WorkoutLog, WorkoutPlan
from tests.test_planner_seam import (
    PLAN,
    easy_sets,
    held_sets,
    install_fake_agent,
    only_draft,
    post_log,
)

# This unit forked from the catch-up integration tip. The diff check below
# uses that commit so earlier units are not counted as this unit's edits.
MERGE_BASE = "932dc8c0f43f031dac8c2d335d2e77da444fe5ac"
ONE_TIME_DIFF_CHECK = pytest.mark.skip(
    reason="One-time check of the original PR's diff. Its base commit is not in this repository."
)
WORKTREE = Path(__file__).resolve().parents[2]
INJURY_TEXT = "Left shoulder impingement (2025)"
PAIN_NOTE = "shoulder pinched"

# Files this unit is not allowed to change. sessions.py, trainer.py, and the
# engine live next to the planner, and her two test files lock the weekly loop.
PROTECTED_PATHS = {
    "backend/app/services/planning_service.py",
    "backend/app/api/v1/endpoints/sessions.py",
    "backend/app/api/v1/endpoints/trainer.py",
    "backend/app/services/progression_engine.py",
    "backend/app/agents/progression_agent.py",
    "backend/tests/test_weekly_loop.py",
    "backend/tests/test_progression_engine.py",
}


@pytest.fixture(autouse=True)
def block_real_planner_network(monkeypatch):
    """Makes a missed test patch fail here instead of calling Anthropic."""

    async def blocked(self, system_prompt, user_message):
        raise AssertionError("Planner trace tests must not call the model network.")

    monkeypatch.setattr(ProgressionPlannerAgent, "_call_anthropic", blocked)


def _as_json(value):
    """Copies a JSON column into plain Python so the session can close.

    SQLite sometimes hands the value back as text. A text value is parsed.
    A list or dict is copied so later asserts do not touch the database.
    """
    if isinstance(value, str):
        return json.loads(value)
    return json.loads(json.dumps(value))


def _set_key(row):
    """The set fields a trace failure is not allowed to change."""
    weight = row.get("weight_lbs")
    if isinstance(weight, (int, float)) and not isinstance(weight, bool):
        weight = float(weight)
    return (
        row.get("exercise_id"),
        row.get("set_num"),
        weight,
        row.get("reps"),
        bool(row.get("pain_flag")),
        row.get("effort"),
    )


async def _refresh_saved(factory, saved):
    """Reads the committed audit rows, logs, and plans into plain dictionaries.

    This runs on the same event loop as the request. The in-memory database
    keeps one connection, and that connection cannot be read from a second
    loop. Callers look at saved after the HTTP call returns.
    """
    async with factory() as db:
        traces = (await db.execute(select(AgentTrace))).scalars().all()
        saved["traces"] = [
            {
                "id": row.id,
                "agent_name": row.agent_name,
                "client_id": row.client_id,
                "model_name": row.model_name,
                "status": row.status,
                "input_summary": row.input_summary or "",
                "output_summary": row.output_summary or "",
                "trace_steps_json": _as_json(row.trace_steps_json),
                "execution_time_ms": row.execution_time_ms,
            }
            for row in traces
        ]
        logs = (await db.execute(select(WorkoutLog))).scalars().all()
        saved["logs"] = [
            {
                "id": row.id,
                "client_id": row.client_id,
                "client_request_id": row.client_request_id,
                "sets": [_set_key(item) for item in (row.extracted_sets_json or [])],
            }
            for row in logs
        ]
        plans = (await db.execute(select(WorkoutPlan))).scalars().all()
        saved["plans"] = [
            {
                "id": row.id,
                "client_id": row.client_id,
                "status": row.status,
                "exercises": _as_json(row.exercises_json),
                "safety_flags": _as_json(row.safety_flags_json),
            }
            for row in plans
        ]
    saved["error"] = None


@pytest.fixture
def api(request):
    """Builds the same temporary database the planner seam tests use.

    Pass injuries through parametrize when a test needs them. The client
    link and the trainer login are stand-ins, so the test can post a log
    without a real account. After each request, saved holds the committed
    rows from that database.
    """
    import asyncio

    options = getattr(request, "param", None) or {}
    injuries = options.get("injuries", [])
    exercises = options.get("exercises", PLAN)
    saved = {"traces": [], "logs": [], "plans": [], "error": None}

    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with factory() as db:
            for index, (sub, email, name) in enumerate(
                [("me", "me@example.com", "Sarah"), ("other", "o@example.com", "Other Client")]
            ):
                trainer = Trainer(supabase_user_id=sub, email=email, full_name=sub)
                db.add(trainer)
                await db.flush()
                client = ClientProfile(
                    trainer_id=trainer.id,
                    full_name=name,
                    injuries_json=injuries if index == 0 else [],
                )
                db.add(client)
                await db.flush()
                db.add(
                    WorkoutPlan(
                        client_id=client.id,
                        week_label="Week 1 - Base",
                        status="approved",
                        exercises_json=exercises if index == 0 else PLAN,
                        safety_flags_json=[],
                    )
                )
            await db.commit()

    asyncio.run(setup())

    async def override_db():
        # The snapshot is taken after the commit, on this same loop, so a
        # trace that rolled back is absent and a trace that saved is present.
        async with factory() as session:
            yield session
            await session.commit()
        try:
            await _refresh_saved(factory, saved)
        except Exception as exc:
            saved["error"] = repr(exc)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_trainer] = lambda: {"sub": "me"}
    app.dependency_overrides[get_current_client_session] = lambda: SimpleNamespace(client_id=1)
    client = TestClient(app)
    yield SimpleNamespace(post=client.post, get=client.get, saved=saved)
    app.dependency_overrides.clear()


def _trace_text(row):
    """Joins the stored summaries and steps so a test can search for injury words."""
    return "\n".join(
        [
            row["input_summary"],
            row["output_summary"],
            json.dumps(row["trace_steps_json"]),
        ]
    )


def _client_plans(api, status):
    """Plans for the logged-in client in one status."""
    return [
        plan
        for plan in api.saved["plans"]
        if plan["client_id"] == 1 and plan["status"] == status
    ]


def _client_logs(api):
    """Workout logs for the logged-in client."""
    return [log for log in api.saved["logs"] if log["client_id"] == 1]


@pytest.mark.parametrize("api", [{"injuries": [INJURY_TEXT]}], indirect=True)
def test_ac_t1_one_model_call_writes_one_trace_row(api, monkeypatch):
    """One successful planner call writes one row with the agent, status, and model."""
    calls, _reply_box = install_fake_agent(
        monkeypatch,
        PlannerReview(
            status="success",
            model_name="claude-haiku-5-5",
            elapsed_ms=18.5,
            flags=[PlannerFlag(exercise_id="ex_squat", message="history is relevant")],
        ),
    )

    response = post_log(api, held_sets(), "ac-t1", has_pain_flag=False)
    assert response.status_code == 201
    assert api.saved["error"] is None
    assert len(calls) == 1
    assert len(api.saved["traces"]) == 1

    row = api.saved["traces"][0]
    assert row["agent_name"] == "ProgressionPlanner"
    assert row["client_id"] == 1
    assert row["status"] == "success"
    assert row["model_name"] == "claude-haiku-5-5"
    assert row["execution_time_ms"] == 18.5
    assert isinstance(row["trace_steps_json"], list) and row["trace_steps_json"]
    assert INJURY_TEXT not in _trace_text(row)
    assert PAIN_NOTE not in _trace_text(row)

    draft = only_draft(api)
    assert any(flag["message"].startswith("[Planner]") for flag in draft["safety_flags"])


@pytest.mark.parametrize("api", [{"injuries": [INJURY_TEXT]}], indirect=True)
def test_ac_t2_no_candidates_writes_no_trace_row(api, monkeypatch):
    """Progressed lifts are not sent to the planner, so no audit row is written."""
    calls, _reply_box = install_fake_agent(
        monkeypatch,
        PlannerReview(
            status="success",
            model_name="claude-haiku-5-5",
            flags=[PlannerFlag(exercise_id="ex_bench", message="should not be asked")],
        ),
    )

    assert post_log(api, easy_sets(), "ac-t2-candidates", has_pain_flag=False).status_code == 201
    assert api.saved["error"] is None
    assert calls == []
    assert api.saved["traces"] == []


def test_ac_t2_no_injury_or_pain_notes_writes_no_trace_row(api, monkeypatch):
    """A held lift with no injury history and no pain notes skips the planner."""
    calls, _reply_box = install_fake_agent(
        monkeypatch,
        PlannerReview(
            status="success",
            model_name="claude-haiku-5-5",
            flags=[PlannerFlag(exercise_id="ex_bench", message="should not be asked")],
        ),
    )

    assert post_log(api, held_sets(), "ac-t2-notes", has_pain_flag=False).status_code == 201
    assert api.saved["error"] is None
    assert calls == []
    assert api.saved["traces"] == []


@pytest.mark.parametrize("api", [{"injuries": [INJURY_TEXT]}], indirect=True)
def test_ac_t2_missing_api_key_writes_no_trace_row(api, monkeypatch):
    """No API key means the planner is not called and no audit row is written."""
    calls, _reply_box = install_fake_agent(
        monkeypatch,
        PlannerReview(
            status="success",
            model_name="claude-haiku-5-5",
            flags=[PlannerFlag(exercise_id="ex_bench", message="should not be asked")],
        ),
        api_key_configured=False,
    )

    assert post_log(api, held_sets(), "ac-t2-key", has_pain_flag=False).status_code == 201
    assert api.saved["error"] is None
    assert calls == []
    assert api.saved["traces"] == []


@pytest.mark.parametrize("api", [{"injuries": [INJURY_TEXT]}], indirect=True)
def test_ac_t3_trace_insert_failure_leaves_draft_flags_and_log_and_returns_201(api, monkeypatch):
    """A forced trace-insert failure still returns 201 and keeps the draft and the log."""
    install_fake_agent(
        monkeypatch,
        PlannerReview(
            status="success",
            model_name="claude-haiku-5-5",
            elapsed_ms=10,
            flags=[
                PlannerFlag(exercise_id="ex_bench", message="keep the bench hold"),
                PlannerFlag(exercise_id="ex_squat", message="keep the squat hold"),
            ],
        ),
    )

    def fail_trace_insert(*args, **kwargs):
        # The row is built inside the savepoint. Raising here is the failed write.
        raise RuntimeError("forced trace insert failure")

    monkeypatch.setattr("app.services.planner_review_service.AgentTrace", fail_trace_insert)

    posted = held_sets()
    response = post_log(api, posted, "ac-t3", has_pain_flag=False)
    assert response.status_code == 201
    assert isinstance(response.json()["id"], int)
    assert api.saved["error"] is None
    assert api.saved["traces"] == []

    draft = only_draft(api)
    bench, squat = draft["exercises"]
    assert (bench["target_reps"], bench["target_weight_lbs"]) == (10, 135.0)
    assert (squat["target_reps"], squat["target_weight_lbs"]) == (12, 185.0)
    assert bench["hold_progression"] is True and squat["hold_progression"] is True
    assert [flag["exercise_id"] for flag in draft["safety_flags"]] == ["ex_bench", "ex_squat"]
    assert all(flag["message"].startswith("[Planner]") for flag in draft["safety_flags"])

    logs = _client_logs(api)
    assert len(logs) == 1
    assert logs[0]["sets"] == [_set_key(row) for row in posted]
    assert len(_client_plans(api, "draft")) == 1
    assert len(_client_plans(api, "approved")) == 1

    # The same request is rejected, which shows the log is still the one we saved.
    # The draft on screen is read again so a rolled-back flag would fail here.
    before = {
        "exercises": draft["exercises"],
        "safety_flags": draft["safety_flags"],
        "log_sets": logs[0]["sets"],
    }
    duplicate = post_log(api, posted, "ac-t3", has_pain_flag=False)
    assert duplicate.status_code == 409
    again = only_draft(api)
    assert again["exercises"] == before["exercises"]
    assert again["safety_flags"] == before["safety_flags"]
    assert _client_logs(api)[0]["sets"] == before["log_sets"]
    assert len(_client_logs(api)) == 1
    assert api.saved["traces"] == []


@pytest.mark.parametrize("api", [{"injuries": [INJURY_TEXT]}], indirect=True)
def test_ac_t4_timeout_writes_one_row_with_status_timeout(api, monkeypatch):
    """A timed-out planner call writes one row whose status is timeout."""
    calls, reply_box = install_fake_agent(
        monkeypatch,
        PlannerReview(
            status="timeout",
            model_name=None,
            elapsed_ms=None,
            flags=[PlannerFlag(exercise_id="ex_squat", message="a stray timeout flag")],
        ),
    )

    timed_out = post_log(api, held_sets(), "ac-t4-review", has_pain_flag=False)
    assert timed_out.status_code == 201
    assert api.saved["error"] is None
    assert len(calls) == 1
    assert len(api.saved["traces"]) == 1
    row = api.saved["traces"][0]
    assert row["agent_name"] == "ProgressionPlanner"
    assert row["status"] == "timeout"
    assert row["model_name"] == "claude-haiku-5-5"
    assert row["execution_time_ms"] >= 0
    assert INJURY_TEXT not in _trace_text(row)
    draft = only_draft(api)
    assert draft["safety_flags"] == []
    assert "a stray timeout flag" not in str(draft["safety_flags"])

    # A timeout that raises, instead of returning a review, is the same status.
    reply_box[0] = TimeoutError("planner timed out")
    raised = post_log(api, held_sets(), "ac-t4-raise", has_pain_flag=False)
    assert raised.status_code == 201
    assert len(calls) == 2
    assert [item["status"] for item in api.saved["traces"]] == ["timeout", "timeout"]
    assert only_draft(api)["safety_flags"] == []


def _changed_paths():
    """Paths this unit changed, including a new file that is not committed yet.

    git diff sees edits to files Git already tracks. git status sees a brand
    new file. Together they are the diff this unit would publish.
    """
    diff = subprocess.run(
        ["git", "diff", "--name-only", MERGE_BASE],
        cwd=WORKTREE,
        capture_output=True,
        text=True,
        check=True,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain", "-uall"],
        cwd=WORKTREE,
        capture_output=True,
        text=True,
        check=True,
    )
    paths = {line.strip() for line in diff.stdout.splitlines() if line.strip()}
    for line in status.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        paths.add(path)
    return paths


def _is_migration(path):
    """True when a path is a database migration this unit must not add."""
    lowered = path.replace("\\", "/").lower()
    return (
        "/alembic/versions/" in f"/{lowered}"
        or lowered.startswith("alembic/versions/")
        or "/migrations/" in f"/{lowered}"
        or lowered.startswith("migrations/")
    )


def _is_protected(path):
    """True for a file or frontend path this unit must leave untouched."""
    normalized = path.replace("\\", "/")
    if normalized in PROTECTED_PATHS:
        return True
    return normalized == "frontend" or normalized.startswith("frontend/")


@ONE_TIME_DIFF_CHECK
def test_ac_t5_diff_adds_no_migration_and_touches_no_protected_file():
    """The unit diff adds no migration and does not touch the protected files."""
    changed = _changed_paths()
    migrations = sorted(path for path in changed if _is_migration(path))
    protected = sorted(path for path in changed if _is_protected(path))
    assert migrations == []
    assert protected == []
