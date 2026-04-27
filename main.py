"""FastAPI app for the StayEase chat agent."""

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel, Field

from agent.db import execute_one, fetch_one
from agent.graph import graph

app = FastAPI(title="StayEase Booking Agent")


class ChatMessageRequest(BaseModel):
    """Request body for sending a guest message."""

    message: str = Field(..., min_length=1)
    guest_name: str | None = None


class SavedMessage(BaseModel):
    """One saved chat message."""

    role: str
    content: str
    created_at: str


def _now() -> str:
    """Return the current UTC time as an ISO string."""
    return datetime.now(timezone.utc).isoformat()


def _load_conversation(conversation_id: str) -> dict[str, Any] | None:
    """Load a conversation row from PostgreSQL."""
    query = """
        SELECT id, messages, current_intent, needs_escalation
        FROM conversations
        WHERE id = %s
        LIMIT 1;
    """
    return fetch_one(query, (conversation_id,))


def _save_conversation(
    conversation_id: str,
    messages: list[dict[str, str]],
    current_intent: str | None,
    needs_escalation: bool,
) -> None:
    """Create or update a conversation row."""
    query = """
        INSERT INTO conversations (
            id,
            messages,
            current_intent,
            needs_escalation,
            updated_at
        )
        VALUES (%s, %s::jsonb, %s, %s, now())
        ON CONFLICT (id)
        DO UPDATE SET
            messages = EXCLUDED.messages,
            current_intent = EXCLUDED.current_intent,
            needs_escalation = EXCLUDED.needs_escalation,
            updated_at = now()
        RETURNING id;
    """
    messages_json = json.dumps(messages)
    execute_one(query, (conversation_id, messages_json, current_intent, needs_escalation))


def _history_to_langchain(messages: list[dict[str, str]]) -> list[BaseMessage]:
    """Convert saved API messages into LangChain messages."""
    converted: list[BaseMessage] = []
    for message in messages:
        if message["role"] == "guest":
            converted.append(HumanMessage(content=message["content"]))
        elif message["role"] == "assistant":
            converted.append(AIMessage(content=message["content"]))
    return converted


def _message_to_dict(role: str, content: str) -> dict[str, str]:
    """Create a saved message dictionary."""
    return {
        "role": role,
        "content": content,
        "created_at": _now(),
    }


def _last_ai_message(messages: list[BaseMessage]) -> AIMessage | None:
    """Find the latest assistant message in the graph result."""
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return message
    return None


@app.post("/api/chat/{conversation_id}/message")
def send_message(
    conversation_id: str,
    request: ChatMessageRequest,
) -> dict[str, Any]:
    """Send one guest message to the StayEase agent."""
    saved = _load_conversation(conversation_id)
    history = saved["messages"] if saved else []

    guest_message = _message_to_dict("guest", request.message)
    langchain_messages = _history_to_langchain(history)
    langchain_messages.append(HumanMessage(content=request.message))

    try:
        result = graph.invoke(
            {
                "messages": langchain_messages,
                "conversation_id": conversation_id,
            }
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Agent service is temporarily unavailable.",
        ) from exc

    final_message = _last_ai_message(result["messages"])
    reply = final_message.content if final_message else "I could not prepare a response."

    updated_history = history + [
        guest_message,
        _message_to_dict("assistant", str(reply)),
    ]
    current_intent = result.get("current_intent")
    needs_escalation = bool(result.get("needs_escalation", False))

    _save_conversation(
        conversation_id,
        updated_history,
        current_intent,
        needs_escalation,
    )

    return {
        "conversation_id": conversation_id,
        "reply": reply,
        "intent": current_intent,
        "tool_results": result.get("tool_results", {}),
    }


@app.get("/api/chat/{conversation_id}/history")
def get_history(conversation_id: str) -> dict[str, Any]:
    """Return saved message history for a conversation."""
    saved = _load_conversation(conversation_id)
    if not saved:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    return {
        "conversation_id": conversation_id,
        "messages": [SavedMessage(**message).model_dump() for message in saved["messages"]],
    }
