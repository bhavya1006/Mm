"""Opens the graph against a saved thread store, so a held run survives to be released."""

from config import constants
from metermind.assistant.graph import build_assistant_graph
from metermind.assistant.state import new_assistant_state

ASSISTANT_OUTCOME_FIELDS = ("answer", "category", "urgency", "tools_called", "steps", "held", "thread_id")


class NoSuchThread(Exception):
    pass


def open_saved_graph(threads_db_path=constants.ASSISTANT_THREADS_PATH):
    import sqlite3

    from langgraph.checkpoint.sqlite import SqliteSaver

    connection = sqlite3.connect(str(threads_db_path), check_same_thread=False)
    checkpointer = SqliteSaver(connection)
    return build_assistant_graph().compile(checkpointer=checkpointer, interrupt_before=["respond"])


def _read_outcome(result, thread_id):
    return {
        "answer": result.get("answer", ""),
        "category": result.get("category", ""),
        "urgency": result.get("urgency", ""),
        "tools_called": [one["tool"] for one in result.get("tool_calls", [])],
        "steps": result.get("steps", []),
        "held": result.get("held", ""),
        "thread_id": thread_id,
    }


def run_assistant(question, thread_id, consumer_category, billing_period, graph):
    state = new_assistant_state(question, consumer_category, billing_period)
    config = {"configurable": {"thread_id": thread_id}}

    result = graph.invoke(state, config=config)

    if not result.get("held") and not result.get("finished") and not result.get("refusal"):
        result = graph.invoke(None, config=config)

    return _read_outcome(result, thread_id)


def release_held_run(thread_id, graph):
    config = {"configurable": {"thread_id": thread_id}}
    current = graph.get_state(config)
    if not current.values:
        raise NoSuchThread(f"no run is waiting on thread {thread_id}")

    result = graph.invoke(None, config=config)
    return _read_outcome(result, thread_id)
