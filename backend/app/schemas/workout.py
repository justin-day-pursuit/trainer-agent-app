"""
Pydantic Schemas for Workouts, Sets, and Logs.

Defines the structured shapes for:
1. Prescribed exercise plans (target reps, target weight).
2. Sets extracted from client voice/chat by Agent 1.
3. Workout log submissions and weekly progression drafts.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PrescribedExercise(BaseModel):
    """An individual exercise prescribed within a weekly workout plan."""
    exercise_id: str = Field(..., description="Unique slug for the exercise, e.g. ex_bench_press")
    name: str = Field(..., description="Common name of exercise, e.g. Barbell Bench Press")
    sets: int = Field(default=3, description="Target number of sets")
    target_reps: int = Field(default=10, description="Target repetitions per set")
    target_weight_lbs: Optional[float] = Field(None, description="Prescribed load in pounds")


class ExtractedSet(BaseModel):
    """A completed set extracted from client speech or chat by Agent 1."""
    exercise_id: str = Field(..., description="Identifier of the exercise performed")
    set_num: int = Field(..., description="Sequence number of the set (1, 2, 3)")
    weight_lbs: Optional[float] = Field(None, description="Weight used in pounds, or null for bodyweight")
    reps: int = Field(..., description="Repetitions completed")
    pain_flag: bool = Field(default=False, description="True if the client reported pain or joint pinching")
    note: Optional[str] = Field(None, description="Client feedback, e.g. 'felt easy', 'pinching in right shoulder'")


class SafetyFlag(BaseModel):
    """Safety concern flagged by Agent 2 during weekly review."""
    severity: str = Field(default="warning", description="info, warning, or critical")
    exercise_id: Optional[str] = Field(None, description="Related exercise")
    message: str = Field(..., description="Human-readable safety note for the trainer")


class WorkoutPlanBase(BaseModel):
    """Base fields for weekly workout plans."""
    week_label: str = Field(..., description="Week identifier, e.g. 2026-W45")
    exercises: List[PrescribedExercise] = Field(default_factory=list)
    safety_flags: List[SafetyFlag] = Field(default_factory=list)
    trainer_notes: Optional[str] = Field(None)


class WorkoutPlanCreate(WorkoutPlanBase):
    """Payload to create or stage a draft workout plan."""
    client_id: int


class WorkoutPlanResponse(WorkoutPlanBase):
    """Workout plan returned via API."""
    id: int
    client_id: int
    status: str = Field(..., description="'draft', 'approved', or 'archived'")
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkoutLogCreate(BaseModel):
    """Client submission containing raw text or voice transcript."""
    plan_id: Optional[int] = Field(None, description="Optional ID of active workout plan")
    raw_input: str = Field(..., min_length=2, description="Natural language workout log message")


class WorkoutLogResponse(BaseModel):
    """Structured response returned after Agent 1 parses the log."""
    id: int
    client_id: int
    plan_id: Optional[int]
    raw_input: str
    extracted_sets: List[ExtractedSet]
    has_pain_flag: bool
    pain_summary: Optional[str]
    logged_at: datetime

    model_config = ConfigDict(from_attributes=True)
