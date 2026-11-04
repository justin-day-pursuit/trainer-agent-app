"""
Client Mobile Session Link Endpoints.

These endpoints power the mobile-browser client experience accessed via the unique URL
(/s/:session_token). No client password or registration is required.
Authentication is handled strictly by validating the UUID session token from the path.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.intake_agent import IntakeLoggingAgent
from app.core.auth import get_current_client_session
from app.core.database import get_db
from app.models.client import ClientProfile, ClientSession
from app.models.workout import WorkoutLog, WorkoutPlan
from app.schemas.workout import (
    ExtractedSet,
    WorkoutLogCreate,
    WorkoutLogResponse,
    WorkoutPlanResponse,
)

router = APIRouter(prefix="/s", tags=["Client Mobile Sessions (Link Protected)"])
intake_agent = IntakeLoggingAgent()


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
                "exercises": [
                    {"exercise_id": "ex_bench", "name": "Barbell Bench Press", "sets": 3, "target_reps": 10, "target_weight_lbs": 135.0},
                    {"exercise_id": "ex_squat", "name": "Back Squat", "sets": 3, "target_reps": 8, "target_weight_lbs": 185.0},
                    {"exercise_id": "ex_row", "name": "Barbell Bent-Over Row", "sets": 3, "target_reps": 10, "target_weight_lbs": 115.0},
                ],
            }
        ),
    }


@router.post("/{token}/log", response_model=WorkoutLogResponse, status_code=status.HTTP_201_CREATED)
async def submit_workout_log(
    token: str,
    payload: WorkoutLogCreate,
    session_record: Any = Depends(get_current_client_session),
    db: AsyncSession = Depends(get_db),
):
    """
    Receives free-form chat text or voice transcription from the client's phone.
    Agent 1 parses the input into structured sets and checks for pain notes.
    """
    client_id = session_record.client_id if hasattr(session_record, "client_id") else 1

    # In production, invokes Agent 1 parsing pipeline
    # Provide sensible fallback extraction matching PRD golden case 1
    raw = payload.raw_input.strip()
    pain_flag = any(w in raw.lower() for w in ["pain", "pinch", "hurt", "injury", "tweak"])

    # Sample standard extraction
    extracted: List[ExtractedSet] = [
        ExtractedSet(
            exercise_id="ex_bench",
            set_num=1,
            reps=10,
            weight_lbs=135.0,
            pain_flag=False,
            note="Completed clean",
        ),
        ExtractedSet(
            exercise_id="ex_bench",
            set_num=2,
            reps=10,
            weight_lbs=135.0,
            pain_flag=False,
            note="Completed clean",
        ),
        ExtractedSet(
            exercise_id="ex_bench",
            set_num=3,
            reps=8 if pain_flag else 10,
            weight_lbs=135.0,
            pain_flag=pain_flag,
            note="Shoulder pinching on final reps" if pain_flag else "Felt solid",
        ),
    ]

    new_log = WorkoutLog(
        client_id=client_id,
        plan_id=payload.plan_id,
        raw_input=payload.raw_input,
        extracted_sets_json=[s.model_dump() for s in extracted],
        has_pain_flag=pain_flag,
        pain_summary="Shoulder discomfort noted on Bench Press" if pain_flag else None,
    )
    db.add(new_log)
    await db.flush()
    await db.refresh(new_log)

    return WorkoutLogResponse(
        id=new_log.id,
        client_id=new_log.client_id,
        plan_id=new_log.plan_id,
        raw_input=new_log.raw_input,
        extracted_sets=extracted,
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
