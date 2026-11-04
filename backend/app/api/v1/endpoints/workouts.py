"""
Workout Plan Management Endpoints (Trainer Protected).

Enables trainers to inspect, manually edit, or stage draft workout programs
for their clients.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_trainer
from app.core.database import get_db
from app.models.workout import WorkoutPlan
from app.schemas.workout import (
    PrescribedExercise,
    SafetyFlag,
    WorkoutPlanCreate,
    WorkoutPlanResponse,
)

router = APIRouter(prefix="/workouts", tags=["Workouts (Trainer Protected)"])


@router.post("/{client_id}/plans", response_model=WorkoutPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_workout_plan(
    client_id: int,
    payload: WorkoutPlanCreate,
    db: AsyncSession = Depends(get_db),
    current_trainer: dict = Depends(get_current_trainer),
):
    """
    Creates a new draft workout plan for a client.
    """
    new_plan = WorkoutPlan(
        client_id=client_id,
        week_label=payload.week_label,
        status="draft",
        exercises_json=[e.model_dump() for e in payload.exercises],
        safety_flags_json=[f.model_dump() for f in payload.safety_flags],
        trainer_notes=payload.trainer_notes,
    )
    db.add(new_plan)
    await db.flush()
    await db.refresh(new_plan)

    return WorkoutPlanResponse(
        id=new_plan.id,
        client_id=new_plan.client_id,
        week_label=new_plan.week_label,
        status=new_plan.status,
        exercises=payload.exercises,
        safety_flags=payload.safety_flags,
        trainer_notes=new_plan.trainer_notes,
        created_at=new_plan.created_at,
        updated_at=new_plan.updated_at,
    )


@router.get("/{client_id}/current", response_model=WorkoutPlanResponse)
async def get_current_workout_plan(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    current_trainer: dict = Depends(get_current_trainer),
):
    """
    Retrieves the active or most recent draft workout plan for a given client.
    """
    stmt = (
        select(WorkoutPlan)
        .where(WorkoutPlan.client_id == client_id)
        .order_by(WorkoutPlan.created_at.desc())
    )
    result = await db.execute(stmt)
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No workout plan found for this client.",
        )

    return WorkoutPlanResponse(
        id=plan.id,
        client_id=plan.client_id,
        week_label=plan.week_label,
        status=plan.status,
        exercises=[PrescribedExercise(**e) for e in (plan.exercises_json or [])],
        safety_flags=[SafetyFlag(**f) for f in (plan.safety_flags_json or [])],
        trainer_notes=plan.trainer_notes,
        approved_at=plan.approved_at,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )
