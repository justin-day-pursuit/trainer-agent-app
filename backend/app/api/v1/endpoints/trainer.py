"""
Trainer Dashboard & Approval Endpoints.

Provides the administrative review feed where personal trainers:
1. Review progression drafts and AI safety flags.
2. Hit the mandatory Human-in-the-Loop "Approve" button to push plans to clients.
3. Inspect Trainer Assistant client adherence alerts (missed check-ins, joint discomfort flags).
"""

import re
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_trainer
from app.core.config import get_settings
from app.core.database import get_db
from app.models.client import ClientProfile, ClientSession
from app.models.trainer import Trainer
from app.models.triage import TriageAlert
from app.models.workout import WorkoutLog, WorkoutPlan
from app.schemas.workout import WorkoutPlanResponse
from app.services.planning_service import generate_next_week_draft, review_summary
from app.services.triage_service import build_triage

router = APIRouter(prefix="/trainer", tags=["Trainer Dashboard (Protected)"])


class ExerciseTargetEdit(BaseModel):
    """One trainer override on a drafted exercise."""
    exercise_id: str
    target_reps: int = Field(..., ge=1, le=100)
    target_weight_lbs: Optional[float] = Field(None, ge=0, le=2000)


class PlanEditRequest(BaseModel):
    """Trainer edits applied to a draft before it is approved."""
    exercises: List[ExerciseTargetEdit]


class BatchApproveRequest(BaseModel):
    """The drafts the trainer saw when they tapped Approve All."""
    plan_ids: List[int] = Field(..., min_length=1, max_length=200)


class StartingExercise(BaseModel):
    """One exercise in a new client's starting plan."""
    name: str = Field(..., min_length=1, max_length=100)
    sets: int = Field(..., ge=1, le=20)
    target_reps: int = Field(..., ge=1, le=100)
    target_weight_lbs: Optional[float] = Field(None, ge=0, le=2000)


class NewClientRequest(BaseModel):
    """Everything needed to get a client started in one step."""
    full_name: str = Field(..., min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    primary_goal: Optional[str] = Field(None, max_length=255)
    injuries: List[str] = Field(default_factory=list)
    exercises: List[StartingExercise] = Field(..., min_length=1, max_length=20)


def build_exercise_rows(exercises: List[StartingExercise]) -> List[dict]:
    """Gives each exercise a stable ID, so its logs line up with its plan week after week."""
    rows: List[dict] = []
    used_ids = set()
    for position, exercise in enumerate(exercises, start=1):
        slug = re.sub(r"[^a-z0-9]+", "_", exercise.name.lower()).strip("_") or str(position)
        exercise_id = f"ex_{slug}"
        if exercise_id in used_ids:
            exercise_id = f"{exercise_id}_{position}"
        used_ids.add(exercise_id)
        rows.append({"exercise_id": exercise_id, **exercise.model_dump()})
    return rows


async def get_trainer_id(db: AsyncSession, current_trainer: dict) -> int:
    """Finds the signed-in trainer's record so every query only touches their own clients."""
    query = select(Trainer.id).limit(1)
    is_local_dev = get_settings().debug and current_trainer.get("sub") == "dev-trainer-uuid"
    if not is_local_dev:
        query = query.where(Trainer.supabase_user_id == current_trainer.get("sub"))
    trainer_id = (await db.execute(query)).scalars().first()
    if trainer_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No trainer account found.")
    return trainer_id


async def get_owned_plan(db: AsyncSession, plan_id: int, trainer_id: int) -> WorkoutPlan:
    """Loads a plan only if it belongs to one of this trainer's clients."""
    result = await db.execute(
        select(WorkoutPlan)
        .join(ClientProfile, WorkoutPlan.client_id == ClientProfile.id)
        .where(WorkoutPlan.id == plan_id, ClientProfile.trainer_id == trainer_id)
    )
    plan = result.scalars().first()
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")
    return plan


async def activate_plan(db: AsyncSession, plan: WorkoutPlan) -> None:
    """Makes a draft the client's live plan and retires the old one, so exactly one stays live."""
    current = await db.execute(
        select(WorkoutPlan).where(WorkoutPlan.client_id == plan.client_id, WorkoutPlan.status == "approved")
    )
    for previous in current.scalars().all():
        previous.status = "archived"
    plan.status = "approved"
    plan.approved_at = datetime.utcnow()


def plan_response(plan: WorkoutPlan) -> WorkoutPlanResponse:
    return WorkoutPlanResponse(
        id=plan.id,
        client_id=plan.client_id,
        week_label=plan.week_label,
        status=plan.status,
        exercises=plan.exercises_json or [],
        safety_flags=plan.safety_flags_json or [],
        trainer_notes=plan.trainer_notes,
        approved_at=plan.approved_at,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@router.get("/dashboard")
async def get_trainer_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_trainer: dict = Depends(get_current_trainer),
):
    """
    Returns dashboard review items for the trainer's Sunday planning cycle.
    """
    trainer_id = await get_trainer_id(db, current_trainer)

    # Fetch this trainer's draft plans awaiting approval
    stmt = (
        select(WorkoutPlan, ClientProfile)
        .join(ClientProfile, WorkoutPlan.client_id == ClientProfile.id)
        .where(WorkoutPlan.status == "draft", ClientProfile.trainer_id == trainer_id)
        .order_by(WorkoutPlan.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    pending_plans = []
    for plan, client in rows:
        last_logged = await db.execute(
            select(func.max(WorkoutLog.logged_at)).where(WorkoutLog.client_id == client.id)
        )
        efforts = {row.get("effort") for row in (plan.exercises_json or []) if row.get("effort")}
        pending_plans.append(
            {
                "id": plan.id,
                "status": "pending_approval",
                **review_summary(plan.exercises_json or []),
                "client_id": client.id,
                "client_name": client.full_name,
                "week_label": plan.week_label,
                "last_workout_at": last_logged.scalar(),
                "overall_effort": "challenging" if "challenging" in efforts else ("easy" if efforts else None),
                "exercises": plan.exercises_json or [],
                "safety_flags": plan.safety_flags_json or [],
            }
        )

    return {
        "pending_drafts_count": len(pending_plans),
        "pending_plans": pending_plans,
    }


@router.get("/triage")
async def get_triage_and_roster(
    db: AsyncSession = Depends(get_db),
    current_trainer: dict = Depends(get_current_trainer),
):
    """
    Returns clients needing attention and the full roster. This is separate from the
    dashboard so a slow check-in draft never holds up the plan review queue.
    """
    trainer_id = await get_trainer_id(db, current_trainer)
    cards, roster = await build_triage(db, trainer_id)
    return {"triage_cards": cards, "roster": roster, "total_active_clients": len(roster)}


@router.post("/triage/{card_id}/dismiss")
async def dismiss_triage_card(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_trainer: dict = Depends(get_current_trainer),
):
    """Hides an alert for good. Only something new about the client can raise another."""
    trainer_id = await get_trainer_id(db, current_trainer)
    result = await db.execute(
        select(TriageAlert)
        .join(ClientProfile, TriageAlert.client_id == ClientProfile.id)
        .where(TriageAlert.id == card_id, ClientProfile.trainer_id == trainer_id)
    )
    alert = result.scalars().first()
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
    alert.dismissed_at = alert.dismissed_at or datetime.utcnow()
    await db.flush()
    return {"id": alert.id, "dismissed": True}


@router.post("/plans/{plan_id}/approve", response_model=WorkoutPlanResponse)
async def approve_workout_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    current_trainer: dict = Depends(get_current_trainer),
):
    """
    Human-in-the-Loop Checkpoint.
    
    The trainer explicitly signs off on an AI-drafted workout progression.
    Changes plan status from 'draft' to 'approved', which instantly makes
    the new week's exercises visible on the client's mobile session link.
    """
    trainer_id = await get_trainer_id(db, current_trainer)
    plan = await get_owned_plan(db, plan_id, trainer_id)
    if plan.status != "draft":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This plan was already reviewed.")

    await activate_plan(db, plan)
    await db.flush()
    await db.refresh(plan)
    return plan_response(plan)


@router.post("/plans/approve-batch")
async def approve_routine_drafts(
    payload: BatchApproveRequest,
    db: AsyncSession = Depends(get_db),
    current_trainer: dict = Depends(get_current_trainer),
):
    """
    Approves the routine drafts the trainer was shown, all in one transaction.
    Anything with pain or a stalled lift is skipped here, so it always gets individual review.
    """
    trainer_id = await get_trainer_id(db, current_trainer)
    result = await db.execute(
        select(WorkoutPlan)
        .join(ClientProfile, WorkoutPlan.client_id == ClientProfile.id)
        .where(
            WorkoutPlan.id.in_(payload.plan_ids),
            WorkoutPlan.status == "draft",
            ClientProfile.trainer_id == trainer_id,
        )
    )
    approved: List[int] = []
    for plan in result.scalars().all():
        if review_summary(plan.exercises_json or [])["review_group"] == "auto_approve":
            await activate_plan(db, plan)
            approved.append(plan.id)
    await db.flush()
    return {"approved_plan_ids": approved, "skipped_plan_ids": sorted(set(payload.plan_ids) - set(approved))}


@router.put("/plans/{plan_id}", response_model=WorkoutPlanResponse)
async def edit_draft_plan(
    plan_id: int,
    payload: PlanEditRequest,
    db: AsyncSession = Depends(get_db),
    current_trainer: dict = Depends(get_current_trainer),
):
    """Applies the trainer's overrides to a draft before it is approved."""
    trainer_id = await get_trainer_id(db, current_trainer)
    plan = await get_owned_plan(db, plan_id, trainer_id)
    if plan.status != "draft":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only drafts can be edited.")

    edits = {edit.exercise_id: edit for edit in payload.exercises}
    updated = []
    for row in plan.exercises_json or []:
        edit = edits.get(row["exercise_id"])
        if edit and (edit.target_reps != row["target_reps"] or edit.target_weight_lbs != row["target_weight_lbs"]):
            row = {
                **row,
                "target_reps": edit.target_reps,
                "target_weight_lbs": edit.target_weight_lbs,
                "reason": "Set by your trainer.",
            }
        updated.append(row)
    plan.exercises_json = updated
    await db.flush()
    await db.refresh(plan)
    return plan_response(plan)


@router.post("/clients", status_code=status.HTTP_201_CREATED)
async def add_client(
    payload: NewClientRequest,
    db: AsyncSession = Depends(get_db),
    current_trainer: dict = Depends(get_current_trainer),
):
    """
    Adds a client with their starting plan and private link in one transaction.
    The trainer wrote this plan themselves, so it goes live without a review step.
    """
    trainer_id = await get_trainer_id(db, current_trainer)
    client = ClientProfile(
        trainer_id=trainer_id,
        full_name=payload.full_name.strip(),
        email=payload.email,
        phone=payload.phone,
        primary_goal=payload.primary_goal,
        injuries_json=[injury.strip() for injury in payload.injuries if injury.strip()],
    )
    db.add(client)
    await db.flush()

    session_token = str(uuid.uuid4())
    db.add(ClientSession(client_id=client.id, session_token=session_token, is_active=True))
    db.add(
        WorkoutPlan(
            client_id=client.id,
            week_label="Week 1 - Starting Plan",
            status="approved",
            exercises_json=build_exercise_rows(payload.exercises),
            safety_flags_json=[],
            approved_at=datetime.utcnow(),
        )
    )
    await db.flush()
    return {"client_id": client.id, "full_name": client.full_name, "session_token": session_token}


@router.post("/clients/{client_id}/plan-next-week", status_code=status.HTTP_201_CREATED)
async def plan_next_week(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    current_trainer: dict = Depends(get_current_trainer),
):
    """Drafts next week on request, for clients whose logs have not produced a draft yet."""
    trainer_id = await get_trainer_id(db, current_trainer)
    owned = await db.execute(
        select(ClientProfile.id).where(ClientProfile.id == client_id, ClientProfile.trainer_id == trainer_id)
    )
    if owned.scalars().first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found.")

    draft = await generate_next_week_draft(db, client_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No logged workouts to draft from yet.")
    return {"plan_id": draft.id, "status": draft.status}
