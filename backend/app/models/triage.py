"""
Triage Alert Database Model.

One row per thing a trainer has been alerted about. It keeps the drafted check-in, so
the model isn't asked again on every page load, and remembers dismissals, so a dismissed
alert stays gone until something new happens with that client.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TriageAlert(Base):
    """An alert for one client, identified by what caused it (alert_key)."""

    __tablename__ = "triage_alerts"
    __table_args__ = (UniqueConstraint("client_id", "alert_key", name="uq_triage_client_alert"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("client_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alert_key: Mapped[str] = mapped_column(String(100), nullable=False)
    draft_message: Mapped[str] = mapped_column(Text, nullable=False)
    dismissed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # The database fills this in when a raw insert omits it. The app also
    # sets it in Python. Both mean "now", so a missed value cannot land blank.
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, server_default=func.now()
    )
