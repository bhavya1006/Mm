"""Two decorators that wrap a call without changing what it returns."""

import functools
import numbers
import time

from metermind.core.exceptions import InvalidReadingError


def reject_negative_readings(wrapped_function):
    @functools.wraps(wrapped_function)
    def wrapper(*args, **kwargs):
        for value in list(args) + list(kwargs.values()):
            if isinstance(value, numbers.Number) and not isinstance(value, bool) and value < 0:
                raise InvalidReadingError(
                    f"{wrapped_function.__name__} was called with a negative value: {value}"
                )
        return wrapped_function(*args, **kwargs)

    return wrapper


def measure_execution_duration(wrapped_function):
    @functools.wraps(wrapped_function)
    def wrapper(*args, **kwargs):
        started_at = time.perf_counter()
        result = wrapped_function(*args, **kwargs)
        wrapper.last_duration_seconds = time.perf_counter() - started_at
        return result

    wrapper.last_duration_seconds = 0.0
    return wrapper


if __name__ == "__main__":
    @measure_execution_duration
    def add_up(numbers_to_add):
        return sum(numbers_to_add)

    result = add_up([1, 2, 3])
    print(
        f"add_up([1, 2, 3]) returned {result} and the wrapper timed it at "
        f"{add_up.last_duration_seconds:.6f} seconds"
    )
