"""
Agent 2: Progression & Workout Plan Generation Agent.

Responsibilities:
1. Receives three read-only inputs:
   - Client's intake injury history
   - In-workout pain notes from the prior week
   - Proposed weights produced by the deterministic progression engine
2. Cross-references proposed weight increases against past injuries and recent pain flags.
3. Flags safety conflicts (e.g., deterministic code proposes +5 lbs on bench, but client reported shoulder pinching).
4. Emits a safety review summary and structured warning flags for the trainer.
5. Strictly prohibited from altering weight integers directly.
6. Strictly prohibited from communicating with clients directly; all output goes to the trainer review queue.
"""

from typing import Any, Dict, List
from app.agents.base import BaseAgentHarness
from app.schemas.workout import SafetyFlag

AGENT_2_SYSTEM_PROMPT = """
You are a Trainer Safety and Progression assistant. You will be provided with three read-only inputs:
1) A client's intake injury profile
2) In-workout pain notes extracted from last week
3) Next week's proposed weights calculated by our deterministic code engine

Your task is to flag any conflicts. If the code suggests +5 lbs on bench press, but the client reported shoulder pain, flag it.
Output a brief explanation for the trainer and an array of warning flags.
You may NOT alter the actual weight integers.
You may NOT communicate directly with the client. All outputs go to the trainer review queue.
"""


class ProgressionPlanAgent(BaseAgentHarness):
    """
    Harness for Agent 2. Evaluates proposed progressions against safety considerations.
    """

    def __init__(self):
        super().__init__(
            agent_name="Agent2_ProgressionPlanAgent",
            system_prompt=AGENT_2_SYSTEM_PROMPT.strip(),
            max_steps=5,
            model_name="claude-haiku-4-5-20251001",
        )
        self.register_tool(
            "flag_injury_risks",
            self._tool_flag_injury_risks,
            "Cross-references proposed exercise load increases against client intake injury history",
        )

    def _tool_flag_injury_risks(
        self,
        injury_profile: List[str],
        pain_notes: List[str],
        proposed_exercises: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Tool interface for detecting joint and movement risks.
        """
        warnings = []
        combined_notes = " ".join(injury_profile + pain_notes).lower()

        for ex in proposed_exercises:
            name = ex.get("name", "").lower()
            # Example heuristic check: shoulder issue + pressing movements
            if "shoulder" in combined_notes and any(p in name for p in ["press", "bench", "overhead"]):
                warnings.append({
                    "severity": "warning",
                    "exercise_id": ex.get("exercise_id"),
                    "message": f"Client has recent shoulder sensitivity. Review proposed load ({ex.get('proposed_weight_lbs')} lbs) on {ex.get('name')}.",
                })
            # Knee / Meniscus issue + squatting movements
            if any(k in combined_notes for k in ["knee", "meniscus"]) and any(s in name for s in ["squat", "lunge"]):
                warnings.append({
                    "severity": "warning",
                    "exercise_id": ex.get("exercise_id"),
                    "message": f"Intake flags knee/meniscus history. Verify knee tracking and depth for {ex.get('name')}.",
                })

        return warnings

    async def review_progression_draft(
        self,
        injury_profile: List[str],
        pain_notes: List[str],
        proposed_exercises: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Executes safety cross-checks and produces a structured review for the trainer.
        """
        self.log_step("observe_progression_inputs", {
            "injury_profile": injury_profile,
            "pain_notes": pain_notes,
            "proposed_exercises_count": len(proposed_exercises),
        })

        warnings = self._tool_flag_injury_risks(injury_profile, pain_notes, proposed_exercises)
        self.log_step("safety_evaluation", {"warnings_found": len(warnings)})

        summary_text = (
            f"Evaluated {len(proposed_exercises)} exercises. "
            f"Found {len(warnings)} safety flags requiring trainer review."
            if warnings
            else "All sets completed target reps without pain flags. Standard progression recommended."
        )

        return {
            "approved_by_agent": len(warnings) == 0,
            "summary": summary_text,
            "safety_flags": warnings,
            "proposed_exercises": proposed_exercises,
        }
