"""Node functions for the StayEase LangGraph agent."""

import os
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

from agent.state import AgentState
from agent.tools import ALL_TOOLS

load_dotenv()

# LangChain's Gemini package reads GOOGLE_API_KEY. These fallbacks support
# common Gemini key names people put in .env files.
if not os.getenv("GOOGLE_API_KEY"):
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("Gemini_API_KEY")
    if gemini_key:
        os.environ["GOOGLE_API_KEY"] = gemini_key

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0)
llm_with_tools = llm.bind_tools(ALL_TOOLS)

SYSTEM_PROMPT = """You are StayEase AI, the virtual booking assistant for StayEase, a short-term rental platform in Bangladesh.

Always begin each interaction by greeting the customer courteously.

Your responsibilities are strictly limited to:
1. Searching for available properties based on location, dates, and number of guests.
2. Providing detailed information about specific listings.
3. Assisting with booking a property when the guest confirms.

If a guest requests anything outside these areas, politely inform them that you will transfer them to a human agent for further assistance.
Always present prices in Bangladeshi Taka (BDT). Remain courteous, concise, and helpful in all interactions."""


def classify_intent(state: AgentState) -> dict[str, Any]:
    """Look at the latest message and figure out what the guest wants."""
    last_message: BaseMessage = state["messages"][-1]
    text = last_message.content.lower()

    if any(word in text for word in ["search", "find", "available", "room", "stay", "looking"]):
        intent = "search"
    elif any(word in text for word in ["detail", "about", "info", "tell me more", "amenities"]):
        intent = "details"
    elif any(word in text for word in ["book", "reserve", "confirm", "yes, book"]):
        intent = "book"
    else:
        intent = "escalate"

    return {
        "current_intent": intent,
        "needs_escalation": intent == "escalate",
    }


def call_llm(state: AgentState) -> dict[str, list[BaseMessage]]:
    """Send the conversation to the LLM and let it decide what to do."""
    system = SystemMessage(content=SYSTEM_PROMPT)
    messages = [system] + list(state["messages"])

    response: AIMessage = llm_with_tools.invoke(messages)

    return {"messages": [response]}


def execute_tool(state: AgentState) -> dict[str, Any]:
    """Run whatever tool the LLM asked for and return the result."""
    tool_map = {t.name: t for t in ALL_TOOLS}
    last_message: AIMessage = state["messages"][-1]

    tool_messages: list[ToolMessage] = []
    tool_output: dict[str, Any] = {}

    for call in last_message.tool_calls:
        tool_name = call["name"]
        if tool_name not in tool_map:
            tool_messages.append(
                ToolMessage(
                    content=f"Tool '{tool_name}' is not available.",
                    tool_call_id=call["id"],
                )
            )
            continue

        result = tool_map[tool_name].invoke(call["args"])
        tool_messages.append(
            ToolMessage(content=str(result), tool_call_id=call["id"])
        )
        tool_output = result if isinstance(result, dict) else {"data": result}

    return {
        "messages": tool_messages,
        "tool_results": tool_output,
    }


def respond(state: AgentState) -> dict[str, list[BaseMessage]]:
    """Take the tool results and have the LLM write a nice response."""
    system = SystemMessage(content=SYSTEM_PROMPT)
    messages = [system] + list(state["messages"])

    response: AIMessage = llm_with_tools.invoke(messages)

    return {"messages": [response]}


def escalate(state: AgentState) -> dict[str, list[BaseMessage]]:
    """Tell the guest we are handing them off to a human."""
    msg = AIMessage(
        content=(
            "I'm sorry, this is outside what I can help with. "
            "Let me connect you with a human agent from StayEase "
            "who can assist you. They'll be with you shortly!"
        )
    )
    return {"messages": [msg]}


# Routing functions

def route_intent(state: AgentState) -> str:
    """After classifying intent, decide where to go next."""
    if state.get("needs_escalation"):
        return "escalate"
    return "call_llm"


def should_use_tool(state: AgentState) -> str:
    """After the LLM responds, check if it wants to call a tool."""
    last_message: BaseMessage = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "execute_tool"
    return "__end__"
