"""Every module in Weeks 6 to 8 that speaks to a model speaks through this one."""

import hashlib
import json
import os
import re
from pathlib import Path

from config import constants

_JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


class LanguageModelError(Exception):
    pass


class ModelNotConfigured(LanguageModelError):
    pass


def load_settings():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ModelNotConfigured(
            "GEMINI_API_KEY is not set; put it in .env before asking the model anything"
        )

    model_name = os.environ.get("GEMINI_MODEL", "").strip() or constants.DEFAULT_LANGUAGE_MODEL
    return {"api_key": api_key, "model_name": model_name}


def _resolved_model_name():
    return os.environ.get("GEMINI_MODEL", "").strip() or constants.DEFAULT_LANGUAGE_MODEL


def cache_key(model_name, prompt):
    digest = hashlib.sha256(f"{model_name}\x1f{prompt}".encode("utf-8"))
    return digest.hexdigest()


def read_cache(cache_path=constants.LANGUAGE_MODEL_CACHE_PATH):
    path = Path(cache_path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as failed:
        raise LanguageModelError(f"the cache at {path} could not be read: {failed}")


def write_cache(cache, cache_path=constants.LANGUAGE_MODEL_CACHE_PATH):
    path = Path(cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache), encoding="utf-8")
    return path


def open_model_client(api_key):
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    return genai


def ask_model(prompt, cache_path=constants.LANGUAGE_MODEL_CACHE_PATH):
    cache = read_cache(cache_path)
    model_name = _resolved_model_name()
    key = cache_key(model_name, prompt)

    if key in cache:
        return cache[key]

    settings = load_settings()
    client = open_model_client(settings["api_key"])

    try:
        model = client.GenerativeModel(settings["model_name"])
        response = model.generate_content(prompt)
        answered = response.text
    except LanguageModelError:
        raise
    except Exception as failed:
        raise LanguageModelError(f"the model could not be reached: {failed}")

    if not answered:
        raise LanguageModelError("the model answered with nothing at all")

    cache[key] = answered
    write_cache(cache, cache_path)
    return answered


def read_answer(said, wanted_keys):
    match = _JSON_OBJECT_PATTERN.search(said)
    if not match:
        raise LanguageModelError(f"no JSON object was found in what the model said: {said[:200]!r}")

    try:
        answered = json.loads(match.group(0))
    except json.JSONDecodeError as failed:
        raise LanguageModelError(f"what the model said could not be read as JSON: {failed}")

    missing = [key for key in wanted_keys if key not in answered]
    if missing:
        raise LanguageModelError(f"the answer is missing: {', '.join(missing)}")

    return answered


def ask_model_with_retry(prompt, cache_path=constants.LANGUAGE_MODEL_CACHE_PATH,
                          attempts=constants.MODEL_RETRY_ATTEMPTS,
                          pause_seconds=constants.MODEL_RETRY_SECONDS, waits=None):
    import time

    last_error = None
    for attempt in range(attempts):
        try:
            return ask_model(prompt, cache_path)
        except ModelNotConfigured:
            raise
        except LanguageModelError as failed:
            last_error = failed
            if attempt < attempts - 1:
                wait_seconds = pause_seconds * (2 ** attempt)
                if waits is not None:
                    waits.append(wait_seconds)
                else:
                    time.sleep(wait_seconds)
    raise last_error


if __name__ == "__main__":
    cache = read_cache()
    print(f"cache holds: {len(cache)} answers")
