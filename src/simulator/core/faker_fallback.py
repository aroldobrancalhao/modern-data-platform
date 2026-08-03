from typing import Callable

from faker.exceptions import UniquenessException


def unique_or_fallback(
    field_name: str,
    generate: Callable[[], str],
    fallback: Callable[[], str],
) -> str:
    """
    Runs a Faker `.unique.*()` call, falling back to a deterministic
    alternative instead of crashing the process when Faker's internal
    uniqueness tracking exhausts its 1,000 retry attempts
    (`faker.exceptions.UniquenessException`).

    This is what actually killed the simulator overnight: `warehouse.
    code` used a 4-digit format (`WH-####`, only 10,000 possible
    values) generated unconditionally every cycle, with nothing
    catching the exception anywhere in the call chain -- confirmed by
    a real traceback recovered from the run's log, at almost exactly
    the 10,000-code mark.
    """
    try:
        return generate()
    except UniquenessException:
        value = fallback()

        print(
            f"WARNING: Faker.unique exhausted for '{field_name}' after "
            f"1,000 attempts -- using fallback value {value!r} instead "
            "of crashing."
        )

        return value
