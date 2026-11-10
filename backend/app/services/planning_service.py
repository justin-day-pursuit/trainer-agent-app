"""
Weekly Planning Service.

Turns a client's logged workouts into a draft of next week's plan for the trainer to
review. The numbers come from the deterministic engine, and nothing reaches the client
until the trainer approves the draft.
"""

import re
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workout import WorkoutLog, WorkoutPlan
from app.schemas.workout import ExtractedSet, PrescribedExercise
from app.services.progression_engine import get_progression_engine
from app.services.planner_review_service import planner_safety_flags


def review_summary(exercises: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Sorts a draft for the trainer. A draft only counts as routine when every exercise
    felt easy, moved up, and had no pain. Everything else needs individual review.
    """
    pain = any(row.get("pain_reported") for row in exercises)
    stalled = any(row.get("hold_progression") or row.get("effort") != "easy" for row in exercises)
    badges = [
        label
        for label, applies in (("Pain Reported", pain), ("Stalled Progression", stalled))
        if applies
    ]
    routine = bool(exercises) and not badges
    return {"review_group": "auto_approve" if routine else "attention_required", "badges": badges}


def _next_week_label(current_label: str) -> str:
    match = re.search(r"Week (\d+)", current_label)
    return f"Week {int(match.group(1)) + 1} - Progression" if match else "Next Week"


async def generate_next_week_draft(db: AsyncSession, client_id: int) -> Optional[WorkoutPlan]:
    """
    Drafts next week's plan from everything logged against the client's current plan.
    A new log replaces any earlier draft, so the trainer only ever reviews the latest.
    Returns None when the client has no approved plan or no logs to work from.
    """
    plan_result = await db.execute(
        select(WorkoutPlan)
        .where(WorkoutPlan.client_id == client_id, WorkoutPlan.status == "approved")
        .order_by(WorkoutPlan.created_at.desc())
        .limit(1)
    )
    current_plan = plan_result.scalars().first()
    if current_plan is None:
        return None

    logs_query = select(WorkoutLog).where(WorkoutLog.client_id == client_id)
    if current_plan.approved_at is not None:
        logs_query = logs_query.where(WorkoutLog.logged_at >= current_plan.approved_at)
    logs_result = await db.execute(logs_query.order_by(WorkoutLog.logged_at.asc()))
    logs = logs_result.scalars().all()
    if not logs:
        return None

    # Clients may split exercises across days, so keep the newest sets for each exercise
    newest_sets: Dict[str, List[ExtractedSet]] = {}
    for log in logs:
        sets = [ExtractedSet(**row) for row in (log.extracted_sets_json or [])]
        for exercise_id in {s.exercise_id for s in sets}:
            newest_sets[exercise_id] = [s for s in sets if s.exercise_id == exercise_id]

    exercises = [PrescribedExercise(**row) for row in current_plan.exercises_json]
    completed_sets = [row for rows in newest_sets.values() for row in rows]
    drafted = get_progression_engine().compute_next_week(exercises, completed_sets)

    safety_flags = [
        {
            "severity": "warning",
            "exercise_id": row["exercise_id"],
            "message": f"[Pain Reported] {row['name']}: {row['pain_note'] or 'pain noted by client'}",
        }
        for row in drafted
        if row["pain_reported"]
    ]
    safety_flags += await planner_safety_flags(db, client_id, drafted)

    earlier_drafts = await db.execute(
        select(WorkoutPlan).where(WorkoutPlan.client_id == client_id, WorkoutPlan.status == "draft")
    )
    for earlier in earlier_drafts.scalars().all():
        earlier.status = "archived"

    draft = WorkoutPlan(
        client_id=client_id,
        week_label=_next_week_label(current_plan.week_label),
        status="draft",
        exercises_json=drafted,
        safety_flags_json=safety_flags,
    )
    db.add(draft)
    await db.flush()
    return draft
