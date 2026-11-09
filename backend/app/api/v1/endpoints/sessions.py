"""
Client Mobile Session Link Endpoints.

These endpoints power the mobile-browser client experience accessed via the unique URL
(/s/:session_token). No client password or registration is required.
Authentication is handled strictly by validating the UUID session token from the path.
"""

import logging
import time
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.intake_agent import IntakeLoggingAgent, WorkoutLoggerUnavailable
from app.core.auth import get_current_client_session
from app.core.database import get_db
from app.models.client import ClientProfile, ClientSession
from app.models.workout import WorkoutLog, WorkoutPlan
from app.schemas.workout import (
    ExtractedSet,
    WorkoutLogCreate,
    WorkoutLogPreviewRequest,
    WorkoutLogPreviewResponse,
    WorkoutLogConfirm,
    WorkoutLogResponse,
    WorkoutPlanResponse,
)

router = APIRouter(prefix="/s", tags=["Client Mobile Sessions (Link Protected)"])
intake_agent = IntakeLoggingAgent()
logger = logging.getLogger(__name__)

# Starter plan shown when a client has no approved plan yet
DEFAULT_EXERCISES: List[Dict[str, Any]] = [
    {"exercise_id": "ex_bench", "name": "Barbell Bench Press", "sets": 3, "target_reps": 10, "target_weight_lbs": 135.0},
    {"exercise_id": "ex_squat", "name": "Back Squat", "sets": 3, "target_reps": 8, "target_weight_lbs": 185.0},
    {"exercise_id": "ex_row", "name": "Barbell Bent-Over Row", "sets": 3, "target_reps": 10, "target_weight_lbs": 115.0},
]


@router.get("/{token}", summary="Retrieve Client Mobile Dashboard")
async def get_client_session_view(
    token: str,
    session_record: Any = Depends(get_current_client_session),
    db: AsyncSession = Depends(get_db),
):
    """
    Validates the client's session token and returns their active training plan.
    """
    client_id = session_record.client_id if hasattr(session_record, "client_id") else 1

    # Fetch client basic profile
    stmt = select(ClientProfile).where(ClientProfile.id == client_id)
    result = await db.execute(stmt)
    client = result.scalar_one_or_none()

    client_name = client.full_name if client else "Athlete"

    # Fetch active approved workout plan
    plan_stmt = (
        select(WorkoutPlan)
        .where(WorkoutPlan.client_id == client_id, WorkoutPlan.status == "approved")
        .order_by(WorkoutPlan.created_at.desc())
    )
    plan_result = await db.execute(plan_stmt)
    active_plan = plan_result.scalar_one_or_none()

    return {
        "client_name": client_name,
        "token": token,
        "active_plan": (
            {
                "id": active_plan.id,
                "week_label": active_plan.week_label,
                "exercises": active_plan.exercises_json or [],
            }
            if active_plan
            else {
                "id": 0,
                "week_label": "Week 1 - Getting Started",
                "exercises": DEFAULT_EXERCISES,
            }
        ),
    }


@router.post("/{token}/log/preview", response_model=WorkoutLogPreviewResponse)
async def preview_workout_log(
    token: str,
    payload: WorkoutLogPreviewRequest,
    session_record: Any = Depends(get_current_client_session),
    db: AsyncSession = Depends(get_db),
):
    """
    Parses client voice or chat text using Workout Logger without writing to the database.
    Returns structured preview sets and flags for the client to review and edit inline.
    """
    start_time = time.perf_counter()
    client_id = session_record.client_id if hasattr(session_record, "client_id") else 1

    # The Workout Logger reads the client's message against today's approved plan
    plan_stmt = (
        select(WorkoutPlan)
        .where(WorkoutPlan.client_id == client_id, WorkoutPlan.status == "approved")
        .order_by(WorkoutPlan.created_at.desc())
        .limit(1)
    )
    plan_result = await db.execute(plan_stmt)
    active_plan = plan_result.scalars().first()
    exercises = (active_plan.exercises_json if active_plan else None) or DEFAULT_EXERCISES

    try:
        parsed = await intake_agent.parse_workout_submission(payload.raw_input.strip(), exercises)
    except WorkoutLoggerUnavailable as exc:
        logger.warning("Workout Logger unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="We couldn't read that workout just now. Your text is saved, so try again.",
        ) from exc

    return WorkoutLogPreviewResponse(
        **parsed,
        model_name=intake_agent.model_name,
        execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2),
    )


@router.post("/{token}/log", response_model=WorkoutLogResponse, status_code=status.HTTP_201_CREATED)
async def submit_workout_log(
    token: str,
    payload: WorkoutLogConfirm,
    session_record: Any = Depends(get_current_client_session),
    db: AsyncSession = Depends(get_db),
):
    """
    Commits the client-confirmed workout log to the database.
    Requires a unique client_request_id for idempotency protection.
    """
    client_id = session_record.client_id if hasattr(session_record, "client_id") else 1

    # Idempotency check: verify client_request_id has not already been committed
    stmt = select(WorkoutLog).where(WorkoutLog.client_request_id == payload.client_request_id)
    result = await db.execute(stmt)
    existing_log = result.scalar_one_or_none()

    if existing_log:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Workout log with request ID '{payload.client_request_id}' has already been recorded.",
        )

    # Persist the confirmed sets reviewed and approved by the client
    new_log = WorkoutLog(
        client_id=client_id,
        plan_id=payload.plan_id,
        client_request_id=payload.client_request_id,
        raw_input=payload.raw_input,
        extracted_sets_json=[s.model_dump() for s in payload.confirmed_sets],
        has_pain_flag=payload.has_pain_flag,
        pain_summary=payload.pain_summary,
    )
    db.add(new_log)
    await db.flush()
    await db.refresh(new_log)

    return WorkoutLogResponse(
        id=new_log.id,
        client_id=new_log.client_id,
        plan_id=new_log.plan_id,
        client_request_id=new_log.client_request_id,
        raw_input=new_log.raw_input,
        extracted_sets=payload.confirmed_sets,
        has_pain_flag=new_log.has_pain_flag,
        pain_summary=new_log.pain_summary,
        logged_at=new_log.logged_at,
    )


@router.get("/{token}/progress", summary="Client Self-Progress History")
async def get_client_progress_history(
    token: str,
    session_record: Any = Depends(get_current_client_session),
    db: AsyncSession = Depends(get_db),
):
    """
    Allows the client to view and map their own week-over-week progress
    directly on their mobile device.
    """
    client_id = session_record.client_id if hasattr(session_record, "client_id") else 1

    stmt = (
        select(WorkoutLog)
        .where(WorkoutLog.client_id == client_id)
        .order_by(WorkoutLog.logged_at.desc())
        .limit(10)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()

    return {
        "client_id": client_id,
        "recent_logs": [
            {
                "id": log.id,
                "logged_at": log.logged_at,
                "sets": log.extracted_sets_json or [],
                "has_pain_flag": log.has_pain_flag,
            }
            for log in logs
        ],
    }
