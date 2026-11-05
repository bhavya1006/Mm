"""Every node the assistant's graph runs, plain functions taking and returning state updates."""

from config import constants

category_model_path = constants.COMPLAINT_CATEGORY_MODEL_PATH
urgency_model_path = constants.COMPLAINT_URGENCY_MODEL_PATH
loaded_classifiers = {}


def _load_classifiers_once():
    if "category" not in loaded_classifiers:
        from metermind.exception_models.baseline_model import load_model
        loaded_classifiers["category"] = load_model(category_model_path)
        loaded_classifiers["urgency"] = load_model(urgency_model_path)
    return loaded_classifiers["category"], loaded_classifiers["urgency"]


def triage_the_question(state):
    question = state.get("question", "")
    if not question or not question.strip():
        return {
            "finished": True,
            "refusal": "there is not enough here to work with",
            "steps": ["triage"],
        }

    category_model, urgency_model = _load_classifiers_once()
    category = category_model.predict([question])[0]
    urgency = urgency_model.predict([question])[0]

    return {"category": category, "urgency": urgency, "steps": ["triage"]}


def run_tools(state):
    from metermind.assistant.tools import READING_TOOLS

    tools_by_name = {one.name: one for one in READING_TOOLS}
    plan = state.get("plan", [])

    for step in plan:
        if step["tool"] not in tools_by_name:
            return {
                "finished": True,
                "refusal": f"the plan named {step['tool']}, which is not a tool that exists",
                "steps": ["tools"],
            }

    tool_calls = []
    for step in plan:
        chosen_tool = tools_by_name[step["tool"]]
        try:
            result = chosen_tool.invoke(step.get("arguments", {}))
        except Exception as failed:
            result = {"error": str(failed)}
        tool_calls.append({
            "tool": step["tool"], "arguments": step.get("arguments", {}), "result": result,
        })

    return {"tool_calls": tool_calls, "steps": ["tools"]}


def approval_gate(state):
    veto = state.get("veto", "")
    if veto:
        return {"held": veto, "answer": constants.HELD_FOR_A_PERSON_REPLY, "steps": ["gate"]}

    for one in state.get("tool_calls", []):
        result = one.get("result", {})
        if isinstance(result, dict) and result.get("exception_class") in constants.HELD_EXCEPTION_CLASSES:
            return {
                "held": result["exception_class"], "answer": constants.HELD_FOR_A_PERSON_REPLY,
                "steps": ["gate"],
            }

    draft = state.get("draft", "")
    if not draft or not draft.strip():
        return {
            "held": "there is nothing to send", "answer": constants.HELD_FOR_A_PERSON_REPLY,
            "steps": ["gate"],
        }

    return {"held": "", "steps": ["gate"]}
