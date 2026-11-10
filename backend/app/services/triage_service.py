"""
Client Triage Service.

Works out who needs the trainer's attention. Urgency is decided here in plain code:

- High: no log in more than 7 days, or pain on the most recent log
- Medium: no log in more than 4 days
- Routine: active and on track

The Trainer Assistant model only writes the check-in message for an alert.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.trainer_agent import TrainerAssistantAgent
from app.models.client import ClientProfile, ClientSession
from app.models.triage import TriageAlert
from app.models.workout import WorkoutLog

HIGH_INACTIVE_DAYS = 7
MEDIUM_INACTIVE_DAYS = 4

assistant = TrainerAssistantAgent()


def compute_urgency(days_inactive: int, pain_on_latest_log: bool) -> str:
    if pain_on_latest_log or days_inactive > HIGH_INACTIVE_DAYS:
        return "high"
    if days_inactive > MEDIUM_INACTIVE_DAYS:
        return "medium"
    return "routine"


def _reason(days_inactive: int, pain: bool, ever_logged: bool) -> str:
    if pain:
        return "Reported pain on their most recent workout."
    if not ever_logged:
        return f"Hasn't logged a first workout in {days_inactive} days."
    return f"No workout logged in {days_inactive} days."


async def _client_rows(db: AsyncSession, trainer_id: int, now: datetime) -> List[Dict[str, Any]]:
    """Gathers each of this trainer's clients with their activity and urgency."""
    result = await db.execute(
        select(ClientProfile)
        .where(ClientProfile.trainer_id == trainer_id)
        .order_by(ClientProfile.full_name.asc())
    )
    rows: List[Dict[str, Any]] = []
    for client in result.scalars().all():
        log_result = await db.execute(
            select(WorkoutLog)
            .where(WorkoutLog.client_id == client.id)
            .order_by(WorkoutLog.logged_at.desc())
            .limit(1)
        )
        last_log = log_result.scalars().first()
        session_result = await db.execute(
            select(ClientSession.session_token)
            .where(ClientSession.client_id == client.id, ClientSession.is_active == True)  # noqa: E712
            .order_by(ClientSession.created_at.desc())
            .limit(1)
        )
        reference = last_log.logged_at if last_log else client.created_at
        days_inactive = max((now - reference).days, 0)
        pain = bool(last_log and last_log.has_pain_flag)
        rows.append(
            {
                "client": client,
                "last_log_id": last_log.id if last_log else None,
                "last_active_at": last_log.logged_at if last_log else None,
                "days_inactive": days_inactive,
                "pain": pain,
                "pain_note": last_log.pain_summary if pain else None,
                "urgency": compute_urgency(days_inactive, pain),
                "session_token": session_result.scalars().first(),
            }
        )
    return rows


def _alert_key(row: Dict[str, Any]) -> str:
    """Names what caused an alert, so something new can raise a new one after a dismissal."""
    cause = "pain" if row["pain"] else f"inactive_{row['urgency']}"
    return f"{cause}:{row['last_log_id'] or 'none'}"


async def build_triage(
    db: AsyncSession, trainer_id: int, now: Optional[datetime] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Returns (triage cards needing attention, the full client roster)."""
    now = now or datetime.utcnow()
    rows = await _client_rows(db, trainer_id, now)
    flagged = [row for row in rows if row["urgency"] != "routine"]

    existing: Dict[Tuple[int, str], TriageAlert] = {}
    if flagged:
        alerts = await db.execute(
            select(TriageAlert).where(TriageAlert.client_id.in_([r["client"].id for r in flagged]))
        )
        existing = {(a.client_id, a.alert_key): a for a in alerts.scalars().all()}

    # Only new alerts need a model call. Saved drafts are reused on every later load.
    new_rows = [r for r in flagged if (r["client"].id, _alert_key(r)) not in existing]
    drafts = await asyncio.gather(
        *[
            assistant.draft_checkin_message(
                r["client"].full_name,
                r["client"].primary_goal,
                r["days_inactive"],
                r["pain"],
                ever_logged=r["last_log_id"] is not None,
                pain_note=r["pain_note"],
            )
            for r in new_rows
        ]
    )
    for row, draft in zip(new_rows, drafts):
        alert = TriageAlert(client_id=row["client"].id, alert_key=_alert_key(row), draft_message=draft)
        db.add(alert)
        existing[(row["client"].id, alert.alert_key)] = alert
    if new_rows:
        await db.flush()

    cards = []
    for row in flagged:
        alert = existing[(row["client"].id, _alert_key(row))]
        if alert.dismissed_at is not None:
            continue
        cards.append(
            {
                "id": alert.id,
                "client_id": row["client"].id,
                "client_name": row["client"].full_name,
                "urgency": row["urgency"],
                "reason": _reason(row["days_inactive"], row["pain"], row["last_log_id"] is not None),
                "draft_message": alert.draft_message,
            }
        )
    cards.sort(key=lambda card: card["urgency"] != "high")

    roster = [
        {
            "client_id": row["client"].id,
            "full_name": row["client"].full_name,
            "primary_goal": row["client"].primary_goal,
            "last_active_at": row["last_active_at"],
            "days_inactive": row["days_inactive"],
            "urgency": row["urgency"],
            "session_token": row["session_token"],
        }
        for row in rows
    ]
    return cards, roster
