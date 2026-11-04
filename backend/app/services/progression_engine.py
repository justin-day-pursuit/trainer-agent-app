"""
Deterministic Progression Engine.

This module is the ONLY authority that calculates exercise weights.
Architectural Rule: No LLM or AI agent ever computes or modifies weight numbers directly.
Agent 2 reads the output of this engine as read-only data, evaluates it against the
client's injury history and pain logs, and flags safety warnings for the trainer.

The engine uses Python's typing.Protocol so that alternative progression strategies
(such as RPE-based progression, wave periodization, or deload weeks) can be plugged
in seamlessly without altering the agent harness.
"""

from typing import Any, Dict, List, Optional, Protocol
from app.schemas.workout import ExtractedSet, PrescribedExercise


class ProposedExerciseChange:
    """Represents the deterministic progression decision for a single exercise."""

    def __init__(
        self,
        exercise_id: str,
        name: str,
        previous_weight_lbs: Optional[float],
        proposed_weight_lbs: Optional[float],
        target_reps: int,
        target_sets: int,
        progression_reason: str,
        hold_progression: bool = False,
    ):
        self.exercise_id = exercise_id
        self.name = name
        self.previous_weight_lbs = previous_weight_lbs
        self.proposed_weight_lbs = proposed_weight_lbs
        self.target_reps = target_reps
        self.target_sets = target_sets
        self.progression_reason = progression_reason
        self.hold_progression = hold_progression

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exercise_id": self.exercise_id,
            "name": self.name,
            "previous_weight_lbs": self.previous_weight_lbs,
            "proposed_weight_lbs": self.proposed_weight_lbs,
            "target_reps": self.target_reps,
            "target_sets": self.target_sets,
            "progression_reason": self.progression_reason,
            "hold_progression": self.hold_progression,
        }


class ProgressionEngine(Protocol):
    """
    Interface definition for any progression calculation engine.
    
    Any class implementing this protocol can be injected into the planning
    pipeline to calculate next week's recommended weights.
    """

    def compute_next_week(
        self,
        current_exercises: List[PrescribedExercise],
        completed_sets: List[ExtractedSet],
        has_pain_flag: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Calculates recommended weights and sets for next week's program.
        """
        ...


class SimpleLinearProgression:
    """
    MVP Progression Engine Implementation.
    
    Standard linear load progression rules:
    - If all prescribed sets met or exceeded target reps without pain:
        -> Add +5.0 lbs to the exercise.
    - If any set missed the target reps:
        -> Hold weight constant (repeat previous weight).
    - If the client reported pain or joint pinching during the exercise:
        -> Hold weight constant and flag for trainer review.
    """

    def __init__(self, default_increment_lbs: float = 5.0):
        self.default_increment_lbs = default_increment_lbs

    def compute_next_week(
        self,
        current_exercises: List[PrescribedExercise],
        completed_sets: List[ExtractedSet],
        has_pain_flag: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Compares last week's prescribed targets against logged sets to produce proposed weights.
        """
        # Group logged sets by exercise_id for easy lookup
        sets_by_exercise: Dict[str, List[ExtractedSet]] = {}
        for s in completed_sets:
            sets_by_exercise.setdefault(s.exercise_id, []).append(s)

        results: List[Dict[str, Any]] = []

        for ex in current_exercises:
            logged = sets_by_exercise.get(ex.exercise_id, [])
            prev_weight = ex.target_weight_lbs or 0.0

            # Case 1: No sets logged for this exercise
            if not logged:
                decision = ProposedExerciseChange(
                    exercise_id=ex.exercise_id,
                    name=ex.name,
                    previous_weight_lbs=ex.target_weight_lbs,
                    proposed_weight_lbs=ex.target_weight_lbs,
                    target_reps=ex.target_reps,
                    target_sets=ex.sets,
                    progression_reason="No sets logged; holding current weight.",
                    hold_progression=True,
                )
                results.append(decision.to_dict())
                continue

            # Check if any set flagged pain
            exercise_pain = any(s.pain_flag for s in logged)
            if exercise_pain or has_pain_flag:
                decision = ProposedExerciseChange(
                    exercise_id=ex.exercise_id,
                    name=ex.name,
                    previous_weight_lbs=ex.target_weight_lbs,
                    proposed_weight_lbs=ex.target_weight_lbs,
                    target_reps=ex.target_reps,
                    target_sets=ex.sets,
                    progression_reason="Pain or pinching noted during sets; holding weight for safety.",
                    hold_progression=True,
                )
                results.append(decision.to_dict())
                continue

            # Check if all sets hit target reps
            all_reps_hit = (len(logged) >= ex.sets) and all(s.reps >= ex.target_reps for s in logged)

            if all_reps_hit and ex.target_weight_lbs is not None:
                # Progress load by increment
                new_weight = prev_weight + self.default_increment_lbs
                decision = ProposedExerciseChange(
                    exercise_id=ex.exercise_id,
                    name=ex.name,
                    previous_weight_lbs=ex.target_weight_lbs,
                    proposed_weight_lbs=new_weight,
                    target_reps=ex.target_reps,
                    target_sets=ex.sets,
                    progression_reason=f"All {ex.sets} sets hit target {ex.target_reps} reps; progressing +{self.default_increment_lbs} lbs.",
                    hold_progression=False,
                )
            else:
                # Hold weight
                decision = ProposedExerciseChange(
                    exercise_id=ex.exercise_id,
                    name=ex.name,
                    previous_weight_lbs=ex.target_weight_lbs,
                    proposed_weight_lbs=ex.target_weight_lbs,
                    target_reps=ex.target_reps,
                    target_sets=ex.sets,
                    progression_reason=f"Target reps not fully completed; holding at {prev_weight} lbs.",
                    hold_progression=True,
                )

            results.append(decision.to_dict())

        return results


def get_progression_engine() -> ProgressionEngine:
    """Factory function returning the active progression engine implementation."""
    return SimpleLinearProgression(default_increment_lbs=5.0)
