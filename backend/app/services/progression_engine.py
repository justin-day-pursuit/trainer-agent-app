"""
Deterministic Progression Engine.

This module is the ONLY authority that calculates exercise weights and reps.
Architectural Rule: No LLM or AI agent ever computes or modifies these numbers directly.

The rule comes from how our partner trainer actually coaches. Reps go up first, inside a
range capped at 12. Weight only goes up once 12 reps feel easy. Anything else holds:

- Pain on the exercise: hold, and flag it for the trainer
- Missed reps: hold
- Felt challenging: hold
- Felt easy, under 12 reps: same weight, +2 reps (never past 12)
- Felt easy, at 12 reps: +5 lbs, back to 8 reps

Every exercise is judged on its own, so pain on bench never holds squats.
The engine uses Python's typing.Protocol so other strategies can be plugged in later.
"""

from typing import Any, Dict, List, Optional, Protocol

from app.schemas.workout import ExtractedSet, PrescribedExercise

MAX_TARGET_REPS = 12
RESET_TARGET_REPS = 8
REP_INCREMENT = 2
WEIGHT_INCREMENT_LBS = 5.0


class ProgressionEngine(Protocol):
    """Interface for any engine that calculates next week's targets."""

    def compute_next_week(
        self,
        current_exercises: List[PrescribedExercise],
        completed_sets: List[ExtractedSet],
    ) -> List[Dict[str, Any]]:
        """Returns one drafted row per prescribed exercise."""
        ...


def _format_weight(weight: Optional[float]) -> str:
    if weight is None:
        return "bodyweight"
    return f"{weight:g} lbs"


class EffortBasedProgression:
    """Applies the reps-first rule to each exercise using last workout's sets and effort."""

    def compute_next_week(
        self,
        current_exercises: List[PrescribedExercise],
        completed_sets: List[ExtractedSet],
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for exercise in current_exercises:
            logged = [s for s in completed_sets if s.exercise_id == exercise.exercise_id]
            results.append(self._draft_exercise(exercise, logged))
        return results

    def _draft_exercise(
        self, exercise: PrescribedExercise, logged: List[ExtractedSet]
    ) -> Dict[str, Any]:
        target_reps = exercise.target_reps
        target_weight = exercise.target_weight_lbs
        efforts = {s.effort for s in logged if s.effort}
        effort = "challenging" if "challenging" in efforts else ("easy" if efforts else None)
        pain_sets = [s for s in logged if s.pain_flag]
        all_reps_hit = len(logged) >= exercise.sets and all(s.reps >= target_reps for s in logged)

        next_reps = target_reps
        next_weight = target_weight
        changed = False

        if not logged:
            reason = "Not logged last week, so targets stay the same."
        elif pain_sets:
            reason = "Pain reported, so weight and reps stay the same."
        elif not all_reps_hit:
            reason = "Missed target reps, so weight and reps stay the same."
        elif effort is None:
            reason = "No effort recorded, so weight and reps stay the same."
        elif effort == "challenging":
            reason = f"Felt challenging at {target_reps} reps, so targets stay the same."
        elif target_reps < MAX_TARGET_REPS:
            next_reps = min(MAX_TARGET_REPS, target_reps + REP_INCREMENT)
            changed = True
            reason = f"Felt easy at {target_reps} reps, so reps go up to {next_reps}."
        elif target_weight is None:
            reason = f"Felt easy at {target_reps} bodyweight reps. Trainer decides the next step."
        else:
            next_weight = target_weight + WEIGHT_INCREMENT_LBS
            next_reps = RESET_TARGET_REPS
            changed = True
            reason = (
                f"Felt easy at {target_reps} reps, so weight goes up "
                f"{WEIGHT_INCREMENT_LBS:g} lbs and reps reset to {next_reps}."
            )

        return {
            "exercise_id": exercise.exercise_id,
            "name": exercise.name,
            "sets": exercise.sets,
            "target_reps": next_reps,
            "target_weight_lbs": next_weight,
            "previous_reps": target_reps,
            "previous_weight_lbs": target_weight,
            "last_reps": [s.reps for s in logged],
            "last_weight_label": _format_weight(logged[0].weight_lbs) if logged else None,
            "effort": effort,
            "pain_reported": bool(pain_sets),
            "pain_note": next((s.note for s in pain_sets if s.note), None),
            "reason": reason,
            "hold_progression": not changed,
        }


def get_progression_engine() -> ProgressionEngine:
    """Factory function returning the active progression engine implementation."""
    return EffortBasedProgression()
