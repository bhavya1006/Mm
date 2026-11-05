"""The assistant, behind two routes: ask, and release what was held."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config import constants
from metermind.api.access_control import require_inspector, require_signed_in
from metermind.assistant.workflow import NoSuchThread, open_saved_graph, release_held_run, run_assistant

router = APIRouter(tags=["assistant"])

assistant_threads_path = constants.ASSISTANT_THREADS_PATH
opened_graph = {}


def _graph_once():
    if "graph" not in opened_graph:
        opened_graph["graph"] = open_saved_graph(assistant_threads_path)
    return opened_graph["graph"]


class AssistantQuestion(BaseModel):
    question: str
    consumer_category: str = ""
    billing_period: str = ""
    thread_id: str


@router.post("/assistant/questions")
def ask_assistant(asked: AssistantQuestion, carried=Depends(require_signed_in)):
    graph = _graph_once()
    return run_assistant(asked.question, asked.thread_id, asked.consumer_category,
                         asked.billing_period, graph)


@router.post("/assistant/threads/{thread_id}/release")
def release_assistant_thread(thread_id: str, carried=Depends(require_inspector)):
    graph = _graph_once()
    try:
        return release_held_run(thread_id, graph)
    except NoSuchThread as refused:
        raise HTTPException(status_code=404, detail=str(refused))
