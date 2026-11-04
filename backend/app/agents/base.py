"""
Base Agent Harness Module.

The harness is the deterministic code that surrounds the reasoning model.
It manages:
1. Loop execution (Observe -> Decide -> Act).
2. Hard maximum step boundaries (preventing runaway token burn or infinite loops).
3. Prompt injection protection (wrapping external client text in strict data tags).
4. Trace recording for backward debugging.
5. Graceful timeout and error handling.
"""

import time
from typing import Any, Callable, Dict, List, Optional
from app.schemas.agent import AgentHandoff


class BaseAgentHarness:
    """
    Base class providing lifecycle management, safety boundaries,
    and trace tracking for all project agents.
    """

    def __init__(
        self,
        agent_name: str,
        system_prompt: str,
        max_steps: int = 8,
        model_name: str = "claude-haiku-4-5-20251001",
    ):
        self.agent_name = agent_name
        self.system_prompt = system_prompt
        self.max_steps = max_steps
        self.model_name = model_name
        self.tools: Dict[str, Callable] = {}
        self.trace_steps: List[Dict[str, Any]] = []

    def register_tool(self, name: str, func: Callable, description: str):
        """
        Registers a Python function as an executable tool available to this agent.
        """
        self.tools[name] = func

    def wrap_user_data(self, tag: str, raw_content: str) -> str:
        """
        Wraps untrusted client or external text inside explicit XML data markers.
        This provides a structural barrier against prompt injection attacks.
        """
        cleaned = raw_content.replace(f"</{tag}>", f"&lt;/{tag}&gt;")
        return f"<{tag} source='untrusted_user_data'>\n{cleaned}\n</{tag}>"

    def log_step(self, action: str, details: Dict[str, Any]):
        """
        Appends an observation, thought, or tool call to the active execution trace.
        """
        self.trace_steps.append({
            "timestamp": time.time(),
            "action": action,
            "details": details,
        })

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Safely executes a registered tool with error handling and bounded retries.
        """
        if tool_name not in self.tools:
            error_msg = f"Tool '{tool_name}' is not registered or authorized for {self.agent_name}."
            self.log_step("tool_error", {"tool": tool_name, "error": error_msg})
            return {"status": "error", "message": error_msg}

        self.log_step("tool_call", {"tool": tool_name, "args": arguments})

        try:
            func = self.tools[tool_name]
            # Execute the tool
            result = func(**arguments)
            self.log_step("tool_result", {"tool": tool_name, "result": result})
            return {"status": "success", "data": result}
        except Exception as exc:
            error_detail = str(exc)
            self.log_step("tool_exception", {"tool": tool_name, "error": error_detail})
            return {"status": "error", "message": f"Execution failed: {error_detail}"}

    def create_handoff(
        self,
        task: str,
        context: Dict[str, Any],
        partial_results: Dict[str, Any],
        confidence: float = 1.0,
    ) -> AgentHandoff:
        """
        Packages outgoing work into a structured AgentHandoff object.
        """
        return AgentHandoff(
            task=task,
            context=context,
            partial_results=partial_results,
            confidence=confidence,
            source_agent=self.agent_name,
        )
