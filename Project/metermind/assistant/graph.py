"""Wires the seven nodes into one graph. A run that has stopped is routed to the end."""

from langgraph.graph import END, StateGraph

from metermind.assistant.agents import critique_draft, draft_answer, plan_tools, write_response
from metermind.assistant.nodes import approval_gate, run_tools, triage_the_question
from metermind.assistant.state import AssistantState

CARRY_ON = "carry_on"

ASSISTANT_NODES = [
    ("triage", triage_the_question),
    ("plan", plan_tools),
    ("tools", run_tools),
    ("draft", draft_answer),
    ("critique", critique_draft),
    ("gate", approval_gate),
    ("respond", write_response),
]


def _stopped_or_carry_on(state):
    if state.get("finished") or state.get("refusal"):
        return END
    return CARRY_ON


def worth_answering(state):
    return _stopped_or_carry_on(state)


def still_going(state):
    return _stopped_or_carry_on(state)


def build_assistant_graph():
    graph = StateGraph(AssistantState)
    for name, function in ASSISTANT_NODES:
        graph.add_node(name, function)

    graph.set_entry_point("triage")
    graph.add_conditional_edges("triage", worth_answering, {CARRY_ON: "plan", END: END})
    graph.add_conditional_edges("plan", still_going, {CARRY_ON: "tools", END: END})
    graph.add_conditional_edges("tools", still_going, {CARRY_ON: "draft", END: END})
    graph.add_edge("draft", "critique")
    graph.add_edge("critique", "gate")
    graph.add_edge("gate", "respond")
    graph.add_edge("respond", END)

    return graph
