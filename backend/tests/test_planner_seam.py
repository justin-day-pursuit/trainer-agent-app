"""
Checks the planner seam on the weekly draft.

The engine still decides every weight and rep. These tests use an in-memory
database and a fake planner, so none of them call the network. A held,
pain-free lift can pick up one [Planner] warning. A progressed lift cannot.
If the fake planner fails, the client's log and the engine's flags still save.
"""

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.agents.progression_agent import PlannerFlag, PlannerReview, ProgressionPlannerAgent
from app.core.auth import get_current_client_session, get_current_trainer
from app.core.database import Base, get_db
from app.main import app
from app.models.client import ClientProfile
from app.models.trainer import Trainer
from app.models.workout import WorkoutPlan

# Same two-lift plan her weekly-loop fixture starts from.
PLAN = [
    {"exercise_id": "ex_bench", "name": "Bench", "sets": 3, "target_reps": 10, "target_weight_lbs": 135.0},
    {"exercise_id": "ex_squat", "name": "Squat", "sets": 3, "target_reps": 12, "target_weight_lbs": 185.0},
]

# Bench can move +2 reps, squat can move +5 lb, and the row can be held.
PROGRESS_PLAN = PLAN + [
    {"exercise_id": "ex_row", "name": "Row", "sets": 3, "target_reps": 10, "target_weight_lbs": 95.0},
]

MERGE_BASE = "1260f3a9270d2d91185e982840692869baa96455"
ONE_TIME_DIFF_CHECK = pytest.mark.skip(
    reason="One-time check of the original PR's diff. Its base commit is not in this repository."
)
WORKTREE = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def block_real_planner_network(monkeypatch):
    """Makes a missed test patch fail here instead of calling Anthropic."""

    async def blocked(self, system_prompt, user_message):
        raise AssertionError("Planner seam tests must not call the model network.")

    monkeypatch.setattr(ProgressionPlannerAgent, "_call_anthropic", blocked)


@pytest.fixture
def api(request):
    """Builds the same temporary database her weekly-loop tests use.

    Pass injuries or a different exercise list through parametrize when a
    test needs them. The client link and the trainer login are stand-ins,
    so the test can post a log without a real account.
    """
    import asyncio

    options = getattr(request, "param", None) or {}
    injuries = options.get("injuries", [])
    exercises = options.get("exercises", PLAN)

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
        async with factory() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_trainer] = lambda: {"sub": "me"}
    app.dependency_overrides[get_current_client_session] = lambda: SimpleNamespace(client_id=1)
    yield TestClient(app)
    app.dependency_overrides.clear()


def install_fake_agent(monkeypatch, reply, api_key_configured=True):
    """Points the draft at a fake planner and records each review it asks for.

    The reply can be a successful review or an exception. Swap reply_box[0]
    later in the test to change what the next draft does. api_key_configured
    lets a test pretend a key is present, or missing, without reading .env.
    """
    calls = []
    reply_box = [reply]

    class FakePlanner:
        def __init__(self, *args, **kwargs):
            # The real agent accepts a caller and a key. The fake ignores both.
            pass

        async def review_held_lifts(self, injuries, pain_notes, candidates):
            calls.append(
                {
                    "injuries": injuries,
                    "pain_notes": list(pain_notes),
                    "exercise_ids": [row.get("exercise_id") for row in candidates],
                }
            )
            current = reply_box[0]
            if isinstance(current, BaseException):
                raise current
            return current

    monkeypatch.setattr("app.services.planner_review_service.ProgressionPlannerAgent", FakePlanner)
    monkeypatch.setattr(
        "app.services.planner_review_service._api_key_is_configured",
        lambda: api_key_configured,
    )
    return calls, reply_box


def log_workout_sets():
    """Copies the set list from her log_workout helper.

    Bench is held because the last set hurt. Squat was easy at 12 reps, so
    the engine adds weight. Neither one is a planner candidate.
    """
    return [
        {
            "exercise_id": "ex_bench",
            "set_num": n,
            "weight_lbs": 135,
            "reps": 10,
            "pain_flag": n == 3,
            "note": "shoulder pinched" if n == 3 else None,
            "effort": "challenging",
        }
        for n in (1, 2, 3)
    ] + [
        {
            "exercise_id": "ex_squat",
            "set_num": n,
            "weight_lbs": 185,
            "reps": 12,
            "pain_flag": False,
            "effort": "easy",
        }
        for n in (1, 2, 3)
    ]


def easy_sets():
    """Copies the set list from her log_easy_workout helper.

    Both lifts were easy and hit the asked-for reps, so both progress.
    The logged weight of 100 is hers; the engine still uses the plan weight.
    """
    return [
        {
            "exercise_id": exercise_id,
            "set_num": n,
            "weight_lbs": 100,
            "reps": target,
            "pain_flag": False,
            "effort": "easy",
        }
        for exercise_id, target in (("ex_bench", 10), ("ex_squat", 12))
        for n in (1, 2, 3)
    ]


def held_sets():
    """Logs both lifts as challenging and pain-free, so the engine holds them."""
    return [
        {
            "exercise_id": exercise_id,
            "set_num": n,
            "weight_lbs": weight,
            "reps": reps,
            "pain_flag": False,
            "effort": "challenging",
        }
        for exercise_id, weight, reps in (("ex_bench", 135, 10), ("ex_squat", 185, 12))
        for n in (1, 2, 3)
    ]


def pain_and_held_sets():
    """Bench reports pain. Squat is challenging and pain-free, so it is held."""
    squat = [
        {
            "exercise_id": "ex_squat",
            "set_num": n,
            "weight_lbs": 185,
            "reps": 12,
            "pain_flag": False,
            "effort": "challenging",
        }
        for n in (1, 2, 3)
    ]
    return log_workout_sets()[:3] + squat


def post_log(api, sets, request_id, has_pain_flag):
    """Posts a confirmed log the same way her helpers do."""
    return api.post(
        "/api/v1/s/t/log",
        json={
            "client_request_id": request_id,
            "raw_input": "x",
            "confirmed_sets": sets,
            "has_pain_flag": has_pain_flag,
        },
    )


def only_draft(api):
    """Returns the single draft on the trainer dashboard."""
    plans = api.get("/api/v1/trainer/dashboard").json()["pending_plans"]
    assert len(plans) == 1
    return plans[0]


def review_snapshot(draft):
    """The fields a planner warning is not allowed to change.

    exercises on the dashboard is the draft's exercises_json. review_group
    and badges are calculated from those rows, not from the safety flags.
    """
    return {
        "exercises_json": draft["exercises"],
        "review_group": draft["review_group"],
        "badges": draft["badges"],
        "status": draft["status"],
        "week_label": draft["week_label"],
    }


def assert_only_engine_flags(draft):
    """The draft kept the pain warning and did not add a planner warning."""
    flags = draft["safety_flags"]
    assert flags
    assert all(flag["message"].startswith("[Pain Reported]") for flag in flags)
    assert all("[Planner]" not in flag["message"] for flag in flags)


@pytest.mark.parametrize(
    "api",
    [{"injuries": ["Left shoulder impingement (2025)"]}],
    indirect=True,
)
def test_ac_s1_injured_client_held_lift_gets_one_planner_flag_after_pain(api, monkeypatch):
    """A held, pain-free squat gets one [Planner] note after the bench pain flag."""
    note = "old shoulder injury is relevant. " + ("keep the load where it is. " * 12)
    assert len(f"[Planner] Squat: {note}") > 320
    calls, _reply_box = install_fake_agent(
        monkeypatch,
        PlannerReview(
            status="success",
            flags=[
                PlannerFlag(exercise_id="ex_squat", message=note),
                PlannerFlag(exercise_id="ex_squat", message="a second squat note is extra"),
                PlannerFlag(exercise_id="ex_bench", message="the painful bench is not a candidate"),
                PlannerFlag(exercise_id="ex_other", message="this exercise is not in the draft"),
            ],
        ),
    )

    response = post_log(api, pain_and_held_sets(), "ac-s1", has_pain_flag=True)
    assert response.status_code == 201
    draft = only_draft(api)
    flags = draft["safety_flags"]

    assert [flag["exercise_id"] for flag in flags] == ["ex_bench", "ex_squat"]
    assert flags[0]["message"].startswith("[Pain Reported] Bench:")
    assert flags[1]["severity"] == "warning"
    assert flags[1]["message"].startswith("[Planner] Squat: old shoulder injury is relevant")
    assert len(flags[1]["message"]) <= 320
    assert flags[1]["message"].endswith("keep the load where it is.")
    assert calls[0]["exercise_ids"] == ["ex_squat"]
    assert calls[0]["injuries"] == ["Left shoulder impingement (2025)"]
    assert calls[0]["pain_notes"] == ["shoulder pinched"]


@pytest.mark.parametrize(
    "api",
    [{"injuries": ["Left shoulder impingement (2025)"], "exercises": PROGRESS_PLAN}],
    indirect=True,
)
def test_ac_s2_progressed_lifts_are_never_flagged_when_the_model_names_them(api, monkeypatch):
    """+2 reps and +5 lb stay unflagged even though the fake names those lifts."""
    calls, _reply_box = install_fake_agent(
        monkeypatch,
        PlannerReview(
            status="success",
            flags=[
                PlannerFlag(exercise_id="ex_bench", message="do not flag the rep increase"),
                PlannerFlag(exercise_id="ex_squat", message="do not flag the weight increase"),
                PlannerFlag(exercise_id="ex_row", message="the held row can be noted"),
            ],
        ),
    )
    sets = [
        {
            "exercise_id": "ex_bench",
            "set_num": n,
            "weight_lbs": 135,
            "reps": 10,
            "pain_flag": False,
            "effort": "easy",
        }
        for n in (1, 2, 3)
    ] + [
        {
            "exercise_id": "ex_squat",
            "set_num": n,
            "weight_lbs": 185,
            "reps": 12,
            "pain_flag": False,
            "effort": "easy",
        }
        for n in (1, 2, 3)
    ] + [
        {
            "exercise_id": "ex_row",
            "set_num": n,
            "weight_lbs": 95,
            "reps": 10,
            "pain_flag": False,
            "effort": "challenging",
        }
        for n in (1, 2, 3)
    ]

    assert post_log(api, sets, "ac-s2", has_pain_flag=False).status_code == 201
    draft = only_draft(api)
    by_id = {row["exercise_id"]: row for row in draft["exercises"]}

    assert (by_id["ex_bench"]["target_reps"], by_id["ex_bench"]["target_weight_lbs"]) == (12, 135.0)
    assert (by_id["ex_squat"]["target_reps"], by_id["ex_squat"]["target_weight_lbs"]) == (8, 190.0)
    assert by_id["ex_row"]["hold_progression"] is True
    assert calls[0]["exercise_ids"] == ["ex_row"]
    planner_ids = [
        flag["exercise_id"]
        for flag in draft["safety_flags"]
        if flag["message"].startswith("[Planner]")
    ]
    assert planner_ids == ["ex_row"]


@pytest.mark.parametrize(
    "api",
    [{"injuries": ["Left shoulder impingement (2025)"]}],
    indirect=True,
)
def test_ac_s3_planner_flags_do_not_change_the_draft_review_fields(api, monkeypatch):
    """Exercises, review group, badges, status, and week label stay the same."""
    install_fake_agent(
        monkeypatch,
        PlannerReview(
            status="success",
            flags=[PlannerFlag(exercise_id="ex_squat", message="shoulder history is relevant")],
        ),
    )
    assert post_log(api, pain_and_held_sets(), "ac-s3-a", has_pain_flag=True).status_code == 201
    with_flags = only_draft(api)
    assert any(flag["message"].startswith("[Planner]") for flag in with_flags["safety_flags"])

    async def no_planner_flags(db, client_id, drafted):
        return []

    monkeypatch.setattr("app.services.planning_service.planner_safety_flags", no_planner_flags)
    assert post_log(api, pain_and_held_sets(), "ac-s3-b", has_pain_flag=True).status_code == 201
    without_flags = only_draft(api)

    assert review_snapshot(with_flags) == review_snapshot(without_flags)
    assert not any(flag["message"].startswith("[Planner]") for flag in without_flags["safety_flags"])
    assert with_flags["review_group"] == "attention_required"
    assert with_flags["status"] == "pending_approval"
    assert with_flags["week_label"].startswith("Week 2")


@pytest.mark.parametrize(
    "api",
    [{"injuries": ["Left shoulder impingement (2025)"]}],
    indirect=True,
)
def test_ac_s4_agent_raise_or_timeout_keeps_the_log_and_engine_flags(api, monkeypatch):
    """A planner crash or timeout still saves the log, the draft, and plan-next-week."""
    calls, reply_box = install_fake_agent(monkeypatch, RuntimeError("planner failed"))

    raised = post_log(api, pain_and_held_sets(), "ac-s4-raise", has_pain_flag=True)
    assert raised.status_code == 201
    assert isinstance(raised.json()["id"], int)
    assert post_log(api, pain_and_held_sets(), "ac-s4-raise", has_pain_flag=True).status_code == 409
    view = api.get("/api/v1/s/t").json()
    assert view["link_status"] == "pending_review"
    assert len(view["last_session"]["sets"]) == 6
    assert_only_engine_flags(only_draft(api))
    assert len(calls) == 1

    reply_box[0] = TimeoutError("planner timed out")
    timed_out = post_log(api, pain_and_held_sets(), "ac-s4-timeout", has_pain_flag=True)
    assert timed_out.status_code == 201
    assert isinstance(timed_out.json()["id"], int)
    assert_only_engine_flags(only_draft(api))
    assert len(calls) == 2

    reply_box[0] = PlannerReview(
        status="timeout",
        flags=[PlannerFlag(exercise_id="ex_squat", message="a stray timeout flag")],
    )
    planned = api.post("/api/v1/trainer/clients/1/plan-next-week")
    assert planned.status_code == 201
    assert planned.json()["status"] == "draft"
    assert_only_engine_flags(only_draft(api))
    assert len(calls) == 3
    assert "a stray timeout flag" not in str(only_draft(api)["safety_flags"])


@pytest.mark.parametrize("api", [{"injuries": ["old knee note"]}], indirect=True)
def test_ac_s5_log_workout_and_log_easy_workout_shapes_never_invoke_the_model(api, monkeypatch):
    """Her two set shapes are not candidates, so the model is not asked."""
    calls, _reply_box = install_fake_agent(
        monkeypatch,
        PlannerReview(
            status="success",
            flags=[
                PlannerFlag(exercise_id="ex_bench", message="should not be asked"),
                PlannerFlag(exercise_id="ex_squat", message="should not be asked"),
            ],
        ),
    )

    assert post_log(api, log_workout_sets(), "ac-s5-log", has_pain_flag=True).status_code == 201
    painful = only_draft(api)
    bench, squat = painful["exercises"]
    assert (bench["target_reps"], bench["target_weight_lbs"]) == (10, 135.0)
    assert (squat["target_reps"], squat["target_weight_lbs"]) == (8, 190.0)
    assert painful["safety_flags"][0]["message"].startswith("[Pain Reported]")
    assert calls == []

    assert post_log(api, easy_sets(), "ac-s5-easy", has_pain_flag=False).status_code == 201
    easy = only_draft(api)
    easy_bench, easy_squat = easy["exercises"]
    assert (easy_bench["target_reps"], easy_bench["target_weight_lbs"]) == (12, 135.0)
    assert (easy_squat["target_reps"], easy_squat["target_weight_lbs"]) == (8, 190.0)
    assert easy["safety_flags"] == []
    assert calls == []


def test_ac_s5_client_with_no_injuries_and_no_pain_notes_never_invokes_the_model(api, monkeypatch):
    """A held lift with an empty injury list and no pain notes skips the model."""
    calls, _reply_box = install_fake_agent(
        monkeypatch,
        PlannerReview(
            status="success",
            flags=[PlannerFlag(exercise_id="ex_bench", message="should not be asked")],
        ),
    )

    assert post_log(api, held_sets(), "ac-s5-empty", has_pain_flag=False).status_code == 201
    draft = only_draft(api)
    bench, squat = draft["exercises"]
    assert bench["hold_progression"] is True and squat["hold_progression"] is True
    assert bench["pain_reported"] is False and squat["pain_reported"] is False
    assert (bench["target_reps"], bench["target_weight_lbs"]) == (10, 135.0)
    assert (squat["target_reps"], squat["target_weight_lbs"]) == (12, 185.0)
    assert draft["safety_flags"] == []
    assert calls == []


@pytest.mark.parametrize(
    "api",
    [{"injuries": ["Left shoulder impingement (2025)"]}],
    indirect=True,
)
def test_missing_api_key_skips_the_model_for_a_held_lift(api, monkeypatch):
    """No key means no model call, even when a held lift and an injury exist."""
    calls, _reply_box = install_fake_agent(
        monkeypatch,
        RuntimeError("the model must not be called without a key"),
        api_key_configured=False,
    )

    assert post_log(api, held_sets(), "no-key", has_pain_flag=False).status_code == 201
    draft = only_draft(api)
    assert draft["exercises"][0]["hold_progression"] is True
    assert draft["safety_flags"] == []
    assert calls == []


@ONE_TIME_DIFF_CHECK
def test_ac_s6_planning_service_diff_has_zero_deleted_lines():
    """The planning service edit only adds the import and the planner call."""
    completed = subprocess.run(
        [
            "git",
            "diff",
            "--numstat",
            MERGE_BASE,
            "--",
            "backend/app/services/planning_service.py",
        ],
        cwd=WORKTREE,
        capture_output=True,
        text=True,
        check=True,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    assert len(lines) == 1, completed.stdout
    added, deleted, path = lines[0].split("\t")
    assert deleted == "0"
    assert int(added) >= 1
    assert path == "backend/app/services/planning_service.py"


@ONE_TIME_DIFF_CHECK
def test_ac_s7_weekly_loop_and_progression_engine_pass_unchanged():
    """Her two test files stay byte-for-byte the same. The full suite runs them."""
    completed = subprocess.run(
        [
            "git",
            "diff",
            "--numstat",
            MERGE_BASE,
            "--",
            "backend/tests/test_weekly_loop.py",
            "backend/tests/test_progression_engine.py",
        ],
        cwd=WORKTREE,
        capture_output=True,
        text=True,
        check=True,
    )
    assert completed.stdout.strip() == ""


def test_a_long_single_sentence_stops_on_a_whole_word():
    """A warning with no sentence break never ends in the middle of a word."""
    from app.services.planner_review_service import PLANNER_MESSAGE_LIMIT, _fit_planner_message

    long_sentence = "[Planner] Bench: " + "shoulder impingement history " * 30
    fitted = _fit_planner_message(long_sentence.strip())
    assert len(fitted) <= PLANNER_MESSAGE_LIMIT
    assert fitted.endswith("…")
    assert fitted[:-1].split(" ")[-1] in {"shoulder", "impingement", "history"}


def test_a_short_warning_is_left_alone():
    from app.services.planner_review_service import _fit_planner_message

    assert _fit_planner_message("[Planner] Bench: short note.") == "[Planner] Bench: short note."
