"""Graph construction for the StayEase LangGraph agent."""

from langgraph.graph import END, StateGraph

from agent.nodes import (
    call_llm,
    classify_intent,
    escalate,
    execute_tool,
    respond,
    route_intent,
    should_use_tool,
)
from agent.state import AgentState


def build_graph() -> StateGraph:
    """Build the workflow graph for the StayEase agent.

    The graph defines the flow of operations based on user input and LLM responses:
        1. Classifying user intent.
        2. Routing to LLM or escalation based on intent.
        3. Deciding whether to execute a tool based on LLM output.
        4. Responding to the user or ending the workflow.
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("call_llm", call_llm)
    workflow.add_node("execute_tool", execute_tool)
    workflow.add_node("respond", respond)
    workflow.add_node("escalate", escalate)

    workflow.set_entry_point("classify_intent")

    # After intent classification, go to the LLM or human escalation.
    workflow.add_conditional_edges(
        "classify_intent",
        route_intent,
        {
            "call_llm": "call_llm",
            "escalate": "escalate",
        },
    )

    # After the LLM, either run a tool or finish the turn.
    workflow.add_conditional_edges(
        "call_llm",
        should_use_tool,
        {
            "execute_tool": "execute_tool",
            "__end__": END,
        },
    )

    # After a tool runs, ask the LLM to write the guest response.
    workflow.add_edge("execute_tool", "respond")
    workflow.add_edge("respond", END)
    workflow.add_edge("escalate", END)

    return workflow.compile()


graph = build_graph()
