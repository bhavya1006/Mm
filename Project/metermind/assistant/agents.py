"""Every prompt the assistant sends, and the four steps it reasons through."""

import json

from config import constants
from metermind.assistant.tools import READING_TOOLS

TOOL_CATALOGUE = {
    tool.name: {
        "does": tool.description,
        "arguments": {
            field_name: str(field.annotation)
            for field_name, field in tool.args_schema.model_fields.items()
        },
    }
    for tool in READING_TOOLS
}

PLANNER_PROMPT = (
    "You are planning which tools to call to answer a consumer's question about their "
    "electricity connection. You may plan up to {rounds} tool calls, in the order they should "
    "run.\n\n"
    "Tools available:\n{catalogue}\n\n"
    "Question: {question}\n"
    "Complaint category: {category}\n"
    "Urgency: {urgency}\n"
    "Consumer category: {consumer_category}\n"
    "Billing period: {billing_period}\n\n"
    "Reply with a JSON object and nothing else, holding two keys: \"plan\" (a list of objects, "
    "each with \"tool\" - the tool's name, exactly as listed above - and \"arguments\" - an "
    "object of arguments for it) and \"reason\" (a short phrase explaining the plan). Name only "
    "tools from the list above."
)

RESOLVER_PROMPT = (
    "Write a draft answer to the consumer's question below, using ONLY the figures and facts "
    "in the tool results. Do not invent any figure that is not in a tool result, and do not "
    "answer anything the tool results do not cover.\n\n"
    "Question: {question}\n\n"
    "Tool results:\n{tool_calls}\n\n"
    "Reply with a JSON object and nothing else, holding two keys: \"draft\" (the draft answer, "
    "in plain words a consumer could read) and \"reason\" (a short phrase saying which tool "
    "result the draft rests on)."
)

CRITIC_PROMPT = (
    "Check the draft answer below against the tool results it is supposed to rest on. Object "
    "only if the draft states a figure or fact that no tool result actually supports.\n\n"
    "Question: {question}\n\n"
    "Draft: {draft}\n\n"
    "Tool results:\n{tool_calls}\n\n"
    "Reply with a JSON object and nothing else, holding two keys: \"veto\" (true if the draft "
    "should be held for a person to check, false if it may go out as written) and \"reason\" "
    "(a short phrase explaining the decision)."
)

RESPONDER_PROMPT = (
    "Rewrite the draft answer below in plain, friendly words a consumer can read, without "
    "changing any figure or fact it states.\n\n"
    "Question: {question}\n\n"
    "Draft: {draft}\n\n"
    "Reply with a JSON object and nothing else, holding two keys: \"reply\" (the rewritten "
    "answer) and \"reason\" (a short phrase saying what changed)."
)

language_model_cache_path = constants.LANGUAGE_MODEL_CACHE_PATH


def build_agent_prompt(template, values):
    from metermind.message_intelligence.llm_client import LanguageModelError

    try:
        return template.format(**values)
    except KeyError as missing:
        raise LanguageModelError(f"the prompt template is missing a value for {missing}")


def plan_tools(state, cache_path=None):
    from metermind.message_intelligence.llm_client import LanguageModelError, ask_model, read_answer

    resolved_cache_path = cache_path if cache_path is not None else language_model_cache_path
    prompt = build_agent_prompt(PLANNER_PROMPT, {
        "catalogue": json.dumps(TOOL_CATALOGUE, indent=2),
        "rounds": constants.ASSISTANT_TOOL_ROUNDS,
        "question": state["question"], "category": state.get("category", ""),
        "urgency": state.get("urgency", ""), "consumer_category": state.get("consumer_category", ""),
        "billing_period": state.get("billing_period", ""),
    })
    answered = ask_model(prompt, resolved_cache_path)
    read = read_answer(answered, ("plan", "reason"))

    plan = read["plan"]
    if not isinstance(plan, list):
        raise LanguageModelError("the plan must be a list of steps, not a sentence")

    return {"plan": plan, "steps": ["plan"]}


def draft_answer(state, cache_path=None):
    from metermind.message_intelligence.llm_client import ask_model, read_answer

    resolved_cache_path = cache_path if cache_path is not None else language_model_cache_path
    told = json.dumps(state.get("tool_calls", []), indent=2, default=str)
    prompt = build_agent_prompt(RESOLVER_PROMPT, {"question": state["question"], "tool_calls": told})
    answered = ask_model(prompt, resolved_cache_path)
    read = read_answer(answered, ("draft", "reason"))
    return {"draft": read["draft"], "steps": ["draft"]}


def critique_draft(state, cache_path=None):
    from metermind.message_intelligence.llm_client import ask_model, read_answer

    resolved_cache_path = cache_path if cache_path is not None else language_model_cache_path
    told = json.dumps(state.get("tool_calls", []), indent=2, default=str)
    prompt = build_agent_prompt(CRITIC_PROMPT, {
        "question": state["question"], "draft": state.get("draft", ""), "tool_calls": told,
    })
    answered = ask_model(prompt, resolved_cache_path)
    read = read_answer(answered, ("veto", "reason"))

    if read["veto"]:
        return {"veto": read["reason"], "steps": ["critique"]}
    return {"veto": "", "steps": ["critique"]}


def write_response(state, cache_path=None):
    from metermind.message_intelligence.llm_client import ask_model, read_answer

    resolved_cache_path = cache_path if cache_path is not None else language_model_cache_path
    prompt = build_agent_prompt(RESPONDER_PROMPT, {
        "question": state["question"], "draft": state.get("draft", ""),
    })
    answered = ask_model(prompt, resolved_cache_path)
    read = read_answer(answered, ("reply", "reason"))
    return {"answer": read["reply"], "steps": ["respond"]}
