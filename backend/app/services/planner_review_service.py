"""
Planner safety flags for a weekly draft.

The progression engine decides the next weights and reps. This file only
adds trainer warnings for lifts the engine held, and it writes one audit
row when that check actually calls the model. It never changes a number,
and a failure here must not throw away the client's log or the draft.
"""

import logging
import math
import time
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import object_session

from app.agents.progression_agent import ProgressionPlannerAgent
from app.core.config import get_settings
from app.models.client import ClientProfile
from app.models.trace import AgentTrace

logger = logging.getLogger(__name__)

# Trainer messages stay short enough to scan on the review card.
# Change this number if the dashboard needs a longer or shorter note.
PLANNER_MESSAGE_LIMIT = 200

# The audit table requires a model name. A timed-out review often has none,
# so we fall back to the model the planner harness is built to call. Keep
# this the same as ProgressionPlannerAgent's model_name.
PLANNER_TRACE_MODEL = "claude-haiku-5-5"


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


def _review_field(review: Any, name: str) -> Any:
    """Reads one field from a planner review object or a plain dictionary.

    The live planner returns a PlannerReview. A test can hand back a
    dictionary with the same keys. A missing review or a missing field
    comes back as None. This does not change the review.
    """
    if review is None:
        return None
    if isinstance(review, dict):
        return review.get(name)
    return getattr(review, name, None)


def _model_name_for_trace(review_model_name: Any, agent: Any) -> str:
    """Picks the model name the audit row is allowed to store.

    The review's own name wins when the call filled one in. A timeout often
    leaves that blank, so we then use the name on the planner harness. The
    last resort is PLANNER_TRACE_MODEL, because the audit table rejects an
    empty model name. The text is cut at 100 characters to fit the column.
    """
    agent_model_name = getattr(agent, "model_name", None)
    for candidate in (review_model_name, agent_model_name, PLANNER_TRACE_MODEL):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()[:100]
    return PLANNER_TRACE_MODEL


def _status_for_trace(status: Any) -> str:
    """Turns the review status into the short word stored on the audit row.

    Success, error, and timeout are the words the rest of the app already
    uses. Anything blank or unexpected is stored as error so the row still
    explains that the check did not succeed. The column holds 50 characters.
    """
    if isinstance(status, str) and status.strip():
        return status.strip()[:50]
    return "error"


def _elapsed_ms(value: Any, started: float) -> float:
    """Chooses how many milliseconds the planner call took.

    The review's own elapsed time is used when the model filled it in.
    Otherwise we use the clock time around the call. A blank, negative, or
    non-numeric time is stored as zero so the audit row can still be saved.
    This does not change the review.
    """
    measured = None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        measured = float(value)
    if measured is None:
        measured = (time.perf_counter() - started) * 1000.0
    if not math.isfinite(measured) or measured < 0:
        measured = 0.0
    return round(measured, 2)


def _input_summary(candidate_count: int, injury_history_present: bool, pain_note_count: int) -> str:
    """Describes what was sent to the planner without copying client words.

    The counts tell a maintainer how much context the check saw. The injury
    list and the pain notes themselves stay out of this sentence. Change
    the wording here if the audit screen needs a different phrase.
    """
    history = "recorded" if injury_history_present else "none"
    return (
        f"Held lifts sent to the planner: {candidate_count}. "
        f"Injury history: {history}. "
        f"Pain notes: {pain_note_count}."
    )


def _output_summary(status: str, flag_count: int, model_name: str) -> str:
    """Describes the planner result without copying injury words.

    The sentence keeps the status, how many warnings we kept, and the model
    name. It does not repeat the model's message, because that message can
    quote the client's injury history. Change it here if the audit screen
    needs another fact.
    """
    return (
        f"Planner status: {status}. "
        f"Warnings kept: {flag_count}. "
        f"Model: {model_name}."
    )


def _trace_steps(
    agent: Any,
    status: str,
    model_name: str,
    candidate_count: int,
    pain_note_count: int,
    injury_history_present: bool,
    flag_count: int,
    elapsed_ms: float,
) -> List[Dict[str, Any]]:
    """Builds the short step list stored on the audit row.

    Step names from the planner harness are kept so someone can see how far
    the check got. The harness's free-text details are left out, because
    those can repeat a client's injury words. The last step records counts
    only. Add a count there if a later screen needs one.
    """
    steps: List[Dict[str, Any]] = []
    recorded = getattr(agent, "trace_steps", None)
    if isinstance(recorded, list):
        for step in recorded:
            if not isinstance(step, dict):
                continue
            action = step.get("action")
            if isinstance(action, str) and action.strip():
                steps.append({"action": action.strip()[:100]})
    steps.append(
        {
            "action": "save_planner_trace",
            "details": {
                "status": status,
                "model_name": model_name,
                "candidate_count": candidate_count,
                "pain_note_count": pain_note_count,
                "injury_history_present": bool(injury_history_present),
                "flag_count": flag_count,
                "execution_time_ms": elapsed_ms,
            },
        }
    )
    return steps


def _detach_failed_trace(db: AsyncSession, trace: Optional[AgentTrace]) -> None:
    """Drops a trace object that did not save, so a later commit cannot insert it.

    A failed savepoint should already forget the object. This is a second
    check for the case where it is still waiting in the session. We only
    detach this one object. The draft and the client's log stay attached.
    """
    if trace is None or object_session(trace) is not db:
        return
    try:
        db.expunge(trace)
    except Exception:
        logger.warning("Could not detach a planner trace that failed to save.")


async def _record_planner_trace(
    db: AsyncSession,
    client_id: int,
    agent: Any,
    review_status: Any,
    review_model_name: Any,
    elapsed_value: Any,
    started: float,
    candidate_count: int,
    injury_history_present: bool,
    pain_note_count: int,
    flag_count: int,
) -> None:
    """Saves one audit row for a planner call that actually ran.

    The insert sits inside a savepoint, which is a bookmark in the current
    database save. If the bookmark write fails, the database returns to that
    bookmark and this function logs the problem without raising. The weekly
    draft, its warning flags, and the client's workout log are left as they
    were. Summaries count what was reviewed. They never copy injury words.

    Maintainers: keep the insert inside begin_nested, and do not re-raise.
    The model name has to be filled in; the audit table rejects a blank one.
    """
    trace = None
    try:
        # The bookmark starts before the row is built. A failure while
        # filling the row, or while writing it, rolls back only this insert.
        async with db.begin_nested():
            model_name = _model_name_for_trace(review_model_name, agent)
            status = _status_for_trace(review_status)
            elapsed_ms = _elapsed_ms(elapsed_value, started)
            trace = AgentTrace(
                agent_name="ProgressionPlanner",
                client_id=client_id,
                model_name=model_name,
                status=status,
                input_summary=_input_summary(
                    candidate_count, injury_history_present, pain_note_count
                ),
                output_summary=_output_summary(status, flag_count, model_name),
                trace_steps_json=_trace_steps(
                    agent,
                    status,
                    model_name,
                    candidate_count,
                    pain_note_count,
                    injury_history_present,
                    flag_count,
                    elapsed_ms,
                ),
                execution_time_ms=elapsed_ms,
            )
            db.add(trace)
            await db.flush()
    except Exception:
        _detach_failed_trace(db, trace)
        logger.exception(
            "Could not save the Progression Planner trace for client %s. "
            "The draft and the client's log were not changed.",
            client_id,
        )


async def planner_safety_flags(
    db: AsyncSession,
    client_id: int,
    drafted: Any,
) -> List[Dict[str, str]]:
    """Adds planner warnings for held, pain-free lifts that did not change weight.

    Called from the weekly draft right after the engine's pain flags are
    built. The returned list is appended to those flags. It is empty when
    there is nothing to review, when the client has no injuries and no pain
    notes, or when no API key is configured. Those three skips do not write
    an audit row. A real model call writes one ProgressionPlanner trace,
    including a timeout. Any error is logged and comes back as an empty list
    so the draft and the client's log still save. A trace that fails to save
    is logged the same way and does not remove the warnings.

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
        # other exercise the reply still names. The audit row is written
        # only after this call, and a failed write does not drop the flags.
        agent = ProgressionPlannerAgent()
        started = time.perf_counter()
        injury_history_present = _has_recorded_text(injuries)
        trace_counts = {
            "candidate_count": len(candidates),
            "injury_history_present": injury_history_present,
            "pain_note_count": len(notes),
        }
        try:
            review = await agent.review_held_lifts(injuries, notes, candidates)
        except TimeoutError:
            await _record_planner_trace(
                db,
                client_id=client_id,
                agent=agent,
                review_status="timeout",
                review_model_name=getattr(agent, "model_name", None),
                elapsed_value=None,
                started=started,
                flag_count=0,
                **trace_counts,
            )
            return []
        except Exception:
            logger.exception(
                "Planner safety check failed for client %s. The draft will keep the engine flags only.",
                client_id,
            )
            await _record_planner_trace(
                db,
                client_id=client_id,
                agent=agent,
                review_status="error",
                review_model_name=getattr(agent, "model_name", None),
                elapsed_value=None,
                started=started,
                flag_count=0,
                **trace_counts,
            )
            return []

        # The harness can still decide not to call the model. That is a skip,
        # and skips do not get an audit row.
        if _review_field(review, "status") == "skipped":
            return []

        flags = _planner_flags(review, candidates)
        await _record_planner_trace(
            db,
            client_id=client_id,
            agent=agent,
            review_status=_review_field(review, "status"),
            review_model_name=_review_field(review, "model_name"),
            elapsed_value=_review_field(review, "elapsed_ms"),
            started=started,
            flag_count=len(flags),
            **trace_counts,
        )
        return flags
    except Exception:
        logger.exception(
            "Planner safety check failed for client %s. The draft will keep the engine flags only.",
            client_id,
        )
        return []
