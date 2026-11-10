"""
Planner safety flags for a weekly draft.

The progression engine decides the next weights and reps. This file only
adds trainer warnings for lifts the engine held. It never changes a number,
and a failure here must not throw away the client's log or the draft.
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.progression_agent import ProgressionPlannerAgent
from app.core.config import get_settings
from app.models.client import ClientProfile

logger = logging.getLogger(__name__)

# Trainer messages stay short enough to scan on the review card.
# Change this number if the dashboard needs a longer or shorter note.
PLANNER_MESSAGE_LIMIT = 200


def _api_key_is_configured() -> bool:
    """True when the app has an Anthropic key and a model call is allowed.

    This reads the same setting the rest of the backend uses. An empty key
    means we skip the planner and leave the draft with the engine's flags
    only. It does not contact the model.
    """
    return bool((get_settings().anthropic_api_key or "").strip())


def _is_candidate_row(row: Any) -> bool:
    """True when this drafted lift is allowed to be sent to the planner.

    A row qualifies only when the engine held it, the client did not report
    pain on it, and the weight is unchanged. A lift that went up in reps or
    weight is not a candidate, even if a model later names it. Painful lifts
    already get an engine flag, so they are left out of this review.
    """
    if not isinstance(row, dict):
        return False
    if row.get("hold_progression") is not True:
        return False
    if row.get("pain_reported") is not False:
        return False
    return row.get("target_weight_lbs") == row.get("previous_weight_lbs")


def _candidate_rows(drafted: Any) -> List[Dict[str, Any]]:
    """Collects at most one candidate row per exercise, in draft order.

    Later steps only ask the planner about this list. The first row for an
    exercise wins, so a repeated id cannot produce a second flag. Rows that
    fail the hold / pain / weight test are ignored. The dictionaries
    themselves are not edited.
    """
    if not isinstance(drafted, (list, tuple)):
        return []

    chosen: List[Dict[str, Any]] = []
    seen = set()
    for row in drafted:
        if not _is_candidate_row(row):
            continue
        exercise_id = row.get("exercise_id")
        if not isinstance(exercise_id, str):
            continue
        exercise_id = exercise_id.strip()
        if not exercise_id or exercise_id in seen:
            continue
        seen.add(exercise_id)
        chosen.append(row)
    return chosen


def _has_recorded_text(value: Any) -> bool:
    """True when an injury entry has words in it.

    Blank strings and empty lists count as nothing recorded. A list counts
    when any item inside it has words. This is how we decide that a client
    has no injury history. It does not rewrite the stored profile.
    """
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple)):
        return any(_has_recorded_text(item) for item in value)
    if isinstance(value, dict):
        return any(_has_recorded_text(item) for item in value.values())
    return True


def _pain_notes(drafted: Any) -> List[str]:
    """Gathers every non-empty pain note from the whole draft.

    Notes are collected from every row, including lifts that are not
    candidates. A blank note is dropped. The returned list is what the
    planner reads; the draft rows stay as the engine wrote them.
    """
    if not isinstance(drafted, (list, tuple)):
        return []

    notes: List[str] = []
    for row in drafted:
        if not isinstance(row, dict):
            continue
        note = row.get("pain_note")
        if not isinstance(note, str):
            continue
        text = note.strip()
        if text:
            notes.append(text)
    return notes


def _flag_parts(flag: Any) -> tuple[Optional[str], Optional[str]]:
    """Reads an exercise id and a message from one model flag.

    The planner may return a small object or a plain dictionary. Anything
    else is treated as unusable. The text is trimmed so a blank message
    can be dropped by the caller.
    """
    if isinstance(flag, dict):
        exercise_id = flag.get("exercise_id")
        message = flag.get("message")
    else:
        exercise_id = getattr(flag, "exercise_id", None)
        message = getattr(flag, "message", None)

    if not isinstance(exercise_id, str) or not isinstance(message, str):
        return None, None
    exercise_id = exercise_id.strip()
    message = message.strip()
    if not exercise_id or not message:
        return None, None
    return exercise_id, message


def _review_flags(review: Any) -> List[Any]:
    """Returns the model's flags only when the review actually succeeded.

    A timeout, a skip, or an error contributes nothing, even if a stray
    flag was attached. That keeps a failed check from adding a warning the
    trainer would treat as a finished review.
    """
    if isinstance(review, dict):
        status = review.get("status")
        flags = review.get("flags")
    else:
        status = getattr(review, "status", None)
        flags = getattr(review, "flags", None)
    if status != "success" or not isinstance(flags, (list, tuple)):
        return []
    return list(flags)


def _planner_flags(review: Any, candidates: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Turns a successful review into trainer warning rows.

    Flags for any exercise that was not a candidate are dropped, and a
    second flag for the same exercise is dropped. The message always starts
    with [Planner], then the exercise name, then the model's text, and it
    is cut at 200 characters. Weights and reps are not copied onto the flag.
    """
    names: Dict[str, str] = {}
    allowed = set()
    for row in candidates:
        exercise_id = row.get("exercise_id")
        if not isinstance(exercise_id, str):
            continue
        exercise_id = exercise_id.strip()
        name = row.get("name")
        if isinstance(name, str) and name.strip():
            names[exercise_id] = name.strip()
        else:
            names[exercise_id] = exercise_id
        allowed.add(exercise_id)

    kept: List[Dict[str, str]] = []
    seen = set()
    for flag in _review_flags(review):
        exercise_id, text = _flag_parts(flag)
        if exercise_id is None or exercise_id not in allowed or exercise_id in seen:
            continue
        message = f"[Planner] {names[exercise_id]}: {text}"
        if len(message) > PLANNER_MESSAGE_LIMIT:
            message = message[:PLANNER_MESSAGE_LIMIT]
        kept.append(
            {
                "severity": "warning",
                "exercise_id": exercise_id,
                "message": message,
            }
        )
        seen.add(exercise_id)
    return kept


async def _load_injuries(db: AsyncSession, client_id: int) -> Any:
    """Reads this client's injury list and does not change it.

    The planner needs the intake injuries as background. Missing clients
    count as no injuries. Callers must not write the value back onto the
    profile.
    """
    result = await db.execute(select(ClientProfile).where(ClientProfile.id == client_id))
    client = result.scalars().first()
    if client is None:
        return []
    return client.injuries_json


async def planner_safety_flags(
    db: AsyncSession,
    client_id: int,
    drafted: Any,
) -> List[Dict[str, str]]:
    """Adds planner warnings for held, pain-free lifts that did not change weight.

    Called from the weekly draft right after the engine's pain flags are
    built. The returned list is appended to those flags. It is empty when
    there is nothing to review, when the client has no injuries and no pain
    notes, or when no API key is configured. Any error is logged and comes
    back as an empty list so the draft and the client's log still save.

    Maintainers: keep the three candidate rules together in
    _is_candidate_row. Do not let this function change targets or re-raise.
    """
    try:
        candidates = _candidate_rows(drafted)
        if not candidates:
            return []

        injuries = await _load_injuries(db, client_id)
        notes = _pain_notes(drafted)
        if not _has_recorded_text(injuries) and not notes:
            return []
        if not _api_key_is_configured():
            return []

        # The agent only sees candidate rows, so a progressed lift is not
        # offered as something it may flag. The mapping below drops any
        # other exercise the reply still names.
        agent = ProgressionPlannerAgent()
        review = await agent.review_held_lifts(injuries, notes, candidates)
        return _planner_flags(review, candidates)
    except Exception:
        logger.exception(
            "Planner safety check failed for client %s. The draft will keep the engine flags only.",
            client_id,
        )
        return []
