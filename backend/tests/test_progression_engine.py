"""
Progression Engine Unit Tests.

Verifies the reps-first rule, one exercise at a time:
1. Easy under 12 reps -> same weight, +2 reps, never past 12.
2. Easy at 12 reps -> +5 lbs, back to 8 reps.
3. Challenging, missed reps, pain, or no effort -> no change.
"""

import pytest

from app.schemas.workout import ExtractedSet, PrescribedExercise
from app.services.progression_engine import EffortBasedProgression


def exercise(exercise_id="ex_bench", reps=10, weight=135.0):
    return PrescribedExercise(
        exercise_id=exercise_id, name=exercise_id, sets=3, target_reps=reps, target_weight_lbs=weight
    )


def logged(reps=(10, 10, 10), weight=135.0, effort="easy", pain_on=None, exercise_id="ex_bench"):
    return [
        ExtractedSet(
            exercise_id=exercise_id,
            set_num=n,
            reps=r,
            weight_lbs=weight,
            effort=effort,
            pain_flag=n == pain_on,
            note="shoulder pinching" if n == pain_on else None,
        )
        for n, r in enumerate(reps, start=1)
    ]


def draft_one(ex, sets):
    return EffortBasedProgression().compute_next_week([ex], sets)[0]


def test_easy_under_twelve_raises_reps_and_keeps_weight():
    row = draft_one(exercise(reps=10), logged())
    assert (row["target_reps"], row["target_weight_lbs"]) == (12, 135.0)
    assert not row["hold_progression"]
    assert "reps go up to 12" in row["reason"]


def test_reps_never_go_past_twelve():
    row = draft_one(exercise(reps=11), logged(reps=(11, 11, 11)))
    assert row["target_reps"] == 12


def test_easy_at_twelve_adds_weight_and_resets_reps():
    row = draft_one(exercise(reps=12), logged(reps=(12, 12, 12)))
    assert (row["target_reps"], row["target_weight_lbs"]) == (8, 140.0)
    assert "5 lbs" in row["reason"]


@pytest.mark.parametrize(
    "sets",
    [
        logged(effort="challenging"),
        logged(reps=(10, 10, 8)),
        logged(reps=(10, 10)),
        logged(effort=None),
        logged(pain_on=3),
        [],
    ],
    ids=["challenging", "missed_reps", "missing_set", "no_effort", "pain", "not_logged"],
)
def test_everything_else_holds(sets):
    row = draft_one(exercise(reps=10), sets)
    assert (row["target_reps"], row["target_weight_lbs"]) == (10, 135.0)
    assert row["hold_progression"]


def test_pain_is_reported_with_the_clients_note():
    row = draft_one(exercise(reps=10), logged(pain_on=3))
    assert row["pain_reported"] is True
    assert row["pain_note"] == "shoulder pinching"


def test_pain_on_bench_does_not_hold_squats():
    """The demo case: easy squats move up while bench holds."""
    engine = EffortBasedProgression()
    plan = [exercise("ex_squat", reps=8, weight=185.0), exercise("ex_bench", reps=10)]
    sets = logged(reps=(8, 8, 8), weight=185.0, exercise_id="ex_squat") + logged(
        reps=(10, 10, 8), effort="challenging", pain_on=3
    )
    squat, bench = engine.compute_next_week(plan, sets)
    assert (squat["target_reps"], squat["target_weight_lbs"]) == (10, 185.0)
    assert not squat["pain_reported"]
    assert (bench["target_reps"], bench["target_weight_lbs"]) == (10, 135.0)
    assert bench["pain_reported"]


def test_bodyweight_at_twelve_is_left_to_the_trainer():
    row = draft_one(exercise(reps=12, weight=None), logged(reps=(12, 12, 12), weight=None))
    assert row["target_weight_lbs"] is None
    assert row["hold_progression"]
