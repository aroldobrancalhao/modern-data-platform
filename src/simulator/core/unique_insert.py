from typing import Callable
from typing import TypeVar

T = TypeVar("T")

DEFAULT_MAX_ATTEMPTS = 10


class UniqueInsertExhausted(RuntimeError):
    pass


def insert_with_unique_retry(
    label: str,
    generate: Callable[[], T],
    insert: Callable[[T], bool],
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> T:
    """
    Calls `insert(entity)` for a freshly `generate()`-d entity. `insert`
    must run `INSERT ... ON CONFLICT DO NOTHING RETURNING <id>` and
    return whether a row actually came back.

    A missing row means one of the entity's UNIQUE fields collided with
    a row already persisted from a *previous* process run -- distinct
    from `faker_fallback.unique_or_fallback`, which only guards against
    Faker's in-process uniqueness tracking running out of combinations.
    Faker's tracking has no idea what is already in Postgres from an
    earlier run, so it cannot prevent this case.

    On collision the entity is discarded (nothing was ever written for
    it) and a brand new one is generated -- cheaper than checking
    existence up front on every insert, since real collisions against a
    space this large are *supposed* to be rare; the retry only pays for
    itself when one actually happens. Gives up loudly after
    `max_attempts`, since that many consecutive collisions is a real
    anomaly worth surfacing, not something to swallow.

    `max_attempts` is defense-in-depth, not the primary fix for a high
    collision rate: it only buys headroom for genuinely rare collisions
    (or a brief unlucky streak). If a `generate()` produces values with
    real per-attempt collision odds much above single-digit percent
    (confirmed for `customer.email` at ~22.6% before its fix -- shallow
    effective entropy in `faker.email()`'s `firstname.lastname@domain`
    pattern, not bad luck), raising this number is not the fix; the
    generator's own value space needs more entropy, the same class of
    problem `warehouse.code` had.
    """
    entity = generate()

    for attempt in range(1, max_attempts + 1):
        if insert(entity):
            return entity

        print(
            f"WARNING: unique constraint collision inserting {label} "
            f"(attempt {attempt}/{max_attempts}) -- a generated unique "
            "field collided with a row already persisted from a "
            "previous run; regenerating and retrying."
        )

        entity = generate()

    raise UniqueInsertExhausted(
        f"Could not insert {label} after {max_attempts} attempts: "
        "unique constraint kept colliding with pre-existing data."
    )
