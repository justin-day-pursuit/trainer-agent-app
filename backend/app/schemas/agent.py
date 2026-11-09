"""
Pydantic Schemas for Agent Handoffs and Orchestration.

Enforces structured, typed data transfer between agents rather than passing
unstructured prose. Prevents context laundering, cascading errors, and hallucinated facts.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentHandoff(BaseModel):
    """
    Standardized payload for passing work from one agent to another.
    
    Contains:
    - task: Explicit instruction of what the receiving agent must do.
    - context: Filtered factual data the receiver requires (not the whole history).
    - partial_results: Any calculations or extractions already completed.
    - confidence: Model confidence score (0.0 to 1.0) so receiver knows reliability.
    - source_agent: Identifier of the initiating agent or engine.
    """
    task: str = Field(..., description="Actionable task description for receiving agent")
    context: Dict[str, Any] = Field(default_factory=dict, description="Filtered facts and entity IDs")
    partial_results: Dict[str, Any] = Field(default_factory=dict, description="Pre-calculated values or flags")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    source_agent: str = Field(..., description="Name of sending agent or system module")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TriageCard(BaseModel):
    """
    Urgency card produced by the Trainer Assistant for display on the Trainer Dashboard.
    
    Alerts the trainer to clients who need attention (missed check-ins, joint pain flags,
    or pending weekly plan approvals).
    """
    client_id: int
    client_name: str
    urgency: str = Field(default="medium", description="'high', 'medium', or 'low'")
    reason: str = Field(..., description="Why this client needs trainer review")
    recommended_action: str = Field(..., description="E.g., 'Approve weekly plan' or 'Send check-in'")
    draft_message: Optional[str] = Field(None, description="Pre-drafted follow-up text for trainer approval")
