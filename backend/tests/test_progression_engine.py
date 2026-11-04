"""
Progression Engine Unit Tests.

Verifies that the deterministic math engine enforces progression rules accurately:
1. All target reps hit -> +5 lbs.
2. Target reps missed -> hold weight constant.
3. Pain flag reported -> hold weight constant for safety.
"""

from app.schemas.workout import ExtractedSet, PrescribedExercise
from app.services.progression_engine import SimpleLinearProgression


def test_progression_all_reps_hit():
    """
    When all 3 sets hit 10 reps, weight should progress by +5 lbs.
    """
    engine = SimpleLinearProgression(default_increment_lbs=5.0)
    exercises = [
        PrescribedExercise(
            exercise_id="ex_bench",
            name="Bench Press",
            sets=3,
            target_reps=10,
            target_weight_lbs=135.0,
        )
    ]
    completed_sets = [
        ExtractedSet(exercise_id="ex_bench", set_num=1, reps=10, weight_lbs=135.0, pain_flag=False),
        ExtractedSet(exercise_id="ex_bench", set_num=2, reps=10, weight_lbs=135.0, pain_flag=False),
        ExtractedSet(exercise_id="ex_bench", set_num=3, reps=10, weight_lbs=135.0, pain_flag=False),
    ]

    results = engine.compute_next_week(exercises, completed_sets, has_pain_flag=False)
    assert len(results) == 1
    bench_result = results[0]
    assert bench_result["proposed_weight_lbs"] == 140.0
    assert not bench_result["hold_progression"]


def test_progression_reps_missed():
    """
    When the client only gets 8 reps on set 3 (target 10), weight should be held.
    """
    engine = SimpleLinearProgression(default_increment_lbs=5.0)
    exercises = [
        PrescribedExercise(
            exercise_id="ex_bench",
            name="Bench Press",
            sets=3,
            target_reps=10,
            target_weight_lbs=135.0,
        )
    ]
    completed_sets = [
        ExtractedSet(exercise_id="ex_bench", set_num=1, reps=10, weight_lbs=135.0, pain_flag=False),
        ExtractedSet(exercise_id="ex_bench", set_num=2, reps=10, weight_lbs=135.0, pain_flag=False),
        ExtractedSet(exercise_id="ex_bench", set_num=3, reps=8, weight_lbs=135.0, pain_flag=False),  # Missed
    ]

    results = engine.compute_next_week(exercises, completed_sets, has_pain_flag=False)
    assert len(results) == 1
    bench_result = results[0]
    assert bench_result["proposed_weight_lbs"] == 135.0
    assert bench_result["hold_progression"]


def test_progression_pain_flag():
    """
    When pain is flagged, weight should be held regardless of reps completed.
    """
    engine = SimpleLinearProgression(default_increment_lbs=5.0)
    exercises = [
        PrescribedExercise(
            exercise_id="ex_bench",
            name="Bench Press",
            sets=3,
            target_reps=10,
            target_weight_lbs=135.0,
        )
    ]
    completed_sets = [
        ExtractedSet(exercise_id="ex_bench", set_num=1, reps=10, weight_lbs=135.0, pain_flag=False),
        ExtractedSet(exercise_id="ex_bench", set_num=2, reps=10, weight_lbs=135.0, pain_flag=False),
        ExtractedSet(exercise_id="ex_bench", set_num=3, reps=10, weight_lbs=135.0, pain_flag=True),  # Pain!
    ]

    results = engine.compute_next_week(exercises, completed_sets, has_pain_flag=False)
    assert len(results) == 1
    bench_result = results[0]
    assert bench_result["proposed_weight_lbs"] == 135.0
    assert bench_result["hold_progression"]
    assert "pain" in bench_result["progression_reason"].lower()
