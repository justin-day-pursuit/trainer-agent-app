"""
Agent 3: Trainer Assistant & Monitoring Agent.

Responsibilities:
1. Monitors client workout adherence patterns, identifying clients who have missed sessions.
2. Organizes dashboard triage alerts based on urgency (e.g., missed check-in > 5 days).
3. Pre-drafts encouraging, personalized follow-up messages for the trainer to inspect.
4. Strictly prohibited from sending messages to clients directly without trainer sign-off.
5. Strictly prohibited from editing workout plans or exercise weights.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List
from app.agents.base import BaseAgentHarness
from app.schemas.agent import TriageCard

AGENT_3_SYSTEM_PROMPT = """
You are a Trainer Administrative Assistant.
Your job is to monitor client training adherence, identify clients who have missed prescribed workouts or check-ins, and prepare concise triage summaries for the trainer.

For clients requiring follow-up, draft a friendly, encouraging check-in message for the trainer's review.
You may NOT send messages to clients directly. All communications require explicit trainer approval.
You may NOT modify workout plans or exercise weights.
"""


class TrainerAssistantAgent(BaseAgentHarness):
    """
    Harness for Agent 3. Generates triage cards and drafts client communication.
    """

    def __init__(self):
        super().__init__(
            agent_name="Agent3_TrainerAssistantAgent",
            system_prompt=AGENT_3_SYSTEM_PROMPT.strip(),
            max_steps=5,
            model_name="claude-3-7-sonnet-20250219",
        )
        self.register_tool(
            "draft_checkin_message",
            self._tool_draft_checkin_message,
            "Drafts a friendly follow-up message tailored to a client's recent adherence",
        )

    def _tool_draft_checkin_message(
        self,
        client_name: str,
        days_inactive: int,
        last_exercise: str = "your last session",
    ) -> str:
        """
        Drafts a supportive message that the trainer can edit or send with one click.
        """
        first_name = client_name.split()[0] if client_name else "there"
        if days_inactive >= 7:
            return (
                f"Hey {first_name}, just checking in! Noticed we haven't logged workouts this week. "
                f"How is everything feeling? Let me know if we need to adjust the schedule or modify any exercises!"
            )
        elif days_inactive >= 4:
            return (
                f"Hi {first_name}, hope your week is going great! Ready for your next session? "
                f"Let me know if you need any adjustments before you hit the gym."
            )
        return f"Hey {first_name}, great work on {last_exercise}! Keep up the strong momentum."

    def generate_client_triage(
        self,
        clients: List[Dict[str, Any]],
    ) -> List[TriageCard]:
        """
        Evaluates client roster adherence and produces sorted triage priority cards.
        """
        triage_cards: List[TriageCard] = []

        for c in clients:
            days_inactive = c.get("days_inactive", 0)
            client_id = c.get("id", 0)
            client_name = c.get("name", "Unknown Client")
            has_pending_plan = c.get("has_pending_plan", False)
            recent_pain = c.get("recent_pain", False)

            if recent_pain:
                triage_cards.append(TriageCard(
                    client_id=client_id,
                    client_name=client_name,
                    urgency="high",
                    reason="Client reported joint pain or discomfort during recent session.",
                    recommended_action="Review workout log and adjust exercise selection.",
                    draft_message=self._tool_draft_checkin_message(client_name, days_inactive),
                ))
            elif has_pending_plan:
                triage_cards.append(TriageCard(
                    client_id=client_id,
                    client_name=client_name,
                    urgency="medium",
                    reason="Upcoming weekly workout plan is drafted and ready for review.",
                    recommended_action="Review and approve draft progression.",
                    draft_message=None,
                ))
            elif days_inactive >= 5:
                triage_cards.append(TriageCard(
                    client_id=client_id,
                    client_name=client_name,
                    urgency="medium",
                    reason=f"No workout logged for {days_inactive} days.",
                    recommended_action="Send check-in message.",
                    draft_message=self._tool_draft_checkin_message(client_name, days_inactive),
                ))

        # Sort: high urgency first
        urgency_order = {"high": 0, "medium": 1, "low": 2}
        triage_cards.sort(key=lambda card: urgency_order.get(card.urgency, 99))
        return triage_cards
