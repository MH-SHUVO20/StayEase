"""State definition for the StayEase booking agent."""

from typing import Any, TypedDict

from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """State object shared across all nodes in the graph.

    Fields:
        messages: Conversation history between the guest and agent.
        conversation_id: Unique ID to track this chat session.
        current_intent: What the guest wants to do (search/details/book/escalate).
        tool_results: Data returned by the last tool call.
        needs_escalation: True if the request is outside the agent's scope.
    """

    messages: list[BaseMessage]
    conversation_id: str
    current_intent: str
    tool_results: dict[str, Any]
    needs_escalation: bool
