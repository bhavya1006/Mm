"""The state that flows through every node of the assistant's graph."""

import operator
from typing import Annotated, TypedDict

ACCUMULATING_CHANNELS = ("steps", "tool_calls")


class AssistantState(TypedDict, total=False):
    question: str
    consumer_category: str
    billing_period: str
    category: str
    urgency: str
    plan: list
    draft: str
    veto: str
    answer: str
    refusal: str
    finished: bool
    held: str
    thread_id: str
    steps: Annotated[list, operator.add]
    tool_calls: Annotated[list, operator.add]


def new_assistant_state(question, consumer_category=None, billing_period=None):
    state = {
        "question": question,
        "consumer_category": consumer_category or "",
        "billing_period": billing_period or "",
        "category": "",
        "urgency": "",
        "plan": [],
        "draft": "",
        "veto": "",
        "answer": "",
        "refusal": "",
        "finished": False,
        "held": "",
        "thread_id": "",
    }
    for channel in ACCUMULATING_CHANNELS:
        state[channel] = []
    return state
