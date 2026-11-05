"""The ladder a case walks, and the one move that goes backwards."""

from config import constants
from metermind.core.exceptions import MeterMindError

ALLOWED_TRANSITIONS = {
    "raised": ("assigned",),
    "assigned": ("inspected", "closed_no_fault"),
    "inspected": ("assigned", "regularised", "billed_back"),
    "regularised": (),
    "billed_back": (),
    "closed_no_fault": (),
}


def move_case_status(current_status, wanted_status):
    if current_status not in ALLOWED_TRANSITIONS:
        raise MeterMindError(f"{current_status} is not a status this platform knows")

    allowed = ALLOWED_TRANSITIONS[current_status]
    if wanted_status not in allowed:
        if allowed:
            raise MeterMindError(
                f"a case at {current_status} may move to {', '.join(allowed)}, "
                f"not to {wanted_status}"
            )
        raise MeterMindError(f"a case at {current_status} is closed and may move nowhere")

    return wanted_status


if __name__ == "__main__":
    print("raised               ->", move_case_status(constants.INITIAL_CASE_STATUS, "assigned"))
    print("assigned             ->", move_case_status("assigned", "inspected"))
    try:
        move_case_status("raised", "closed_no_fault")
    except MeterMindError as refused:
        print(f"raised               -> closed_no_fault      refused: {refused}")
