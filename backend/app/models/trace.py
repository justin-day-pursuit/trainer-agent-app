"""
Agent Observability and Trace Logging Model.

Stores step-by-step audit records for every agent invocation, tool call,
and decision. This allows developers to distinguish between LLM reasoning errors
and harness execution bugs using backward trace analysis.
"""

from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base


class AgentTrace(Base):
    """
    SQLAlchemy model recording an agent execution trace.
    
    Tracks which model ran, what prompt context was fed, what tools were called,
    what confidence score was reported, and how long execution took.
    """
    __tablename__ = "agent_traces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    client_id: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=True)

    # Model metadata (e.g. 'claude-3-5-sonnet', fallback reasons if any)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="success", nullable=False)  # success, error, timeout

    # Context and results
    input_summary: Mapped[str] = mapped_column(Text, nullable=True)
    output_summary: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Detailed chronological steps (model thoughts, tool arguments, tool results)
    trace_steps_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=list, nullable=False
    )

    execution_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
