"""State definition for the StayEase booking agent."""

from typing import Annotated, Any, NotRequired, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State object shared across all nodes in the graph.

    Fields:
    messages: Conversation history between the guest and agent.
    conversation_id: Unique ID to track this chat session.
    current_intent: What the guest wants to do (search/details/book/escalate).
    tool_results: Data returned by the last tool call.
    needs_escalation: True if the request is outside the agent's scope.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    conversation_id: str
    current_intent: NotRequired[str]
    tool_results: NotRequired[dict[str, Any]]
    needs_escalation: NotRequired[bool]
