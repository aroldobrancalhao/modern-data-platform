from psycopg import Connection


class BatchWriter:
    """
    Buffers INSERT rows across multiple simulator cycles and flushes
    them as one multi-row INSERT per table once the total buffered
    row count reaches `flush_threshold` (SIMULATOR_INSERT_BATCH_SIZE).

    Uses a hand-built multi-row VALUES clause -- the psycopg3
    equivalent of psycopg2's `execute_values` (psycopg3 has no
    `psycopg.extras` module) -- instead of `executemany()`: without
    pipeline mode, psycopg3's `executemany()` still issues one network
    round trip per row, which would not touch the actual bottleneck
    (connection/query wait time, confirmed via cProfile in the
    previous perf fix). A single multi-row INSERT sends the whole
    batch in one round trip. COPY would be faster still but is
    unnecessary at this volume (on the order of 100k rows total, not
    billions).

    Tables are flushed in the order they were first added to within
    this writer's lifetime (a plain dict, insertion-ordered since
    Python 3.7).

    Every table still written through this class (customer_addresses,
    order_items, order_status_history, payments, shipments, reviews,
    inventory_movements) references only rows inserted immediately
    and synchronously (sellers, categories, products, warehouses,
    inventories, customers, orders -- see the repositories/services
    for those entities) -- never another buffered table. So unlike an
    earlier version of this design, flush order between buffered
    tables no longer matters for FK correctness: every parent a
    buffered row can reference is already present in this same
    transaction (read-your-own-writes) by the time it is generated,
    regardless of when this writer flushes.

    Deliberately excludes warehouses/inventory/sellers/categories/
    products/customers/orders (see their own repositories):
    inventory quantity is mutated in place by orders
    (`decrease_available_quantity`), which depends on real,
    immediately-consistent state -- buffering that alongside plain
    inserts would risk overselling stock against a stale snapshot.
    The others moved to immediate, synchronously-confirmed inserts
    (`INSERT ... RETURNING`, see `unique_insert.py`) because something
    buffered and downstream (a child row, or a later cycle picking
    this row's id out of `ReferencePool`) needs to know *now* whether
    the row actually made it into the table, not several cycles later
    at flush time -- a `RETURNING` check that comes back empty means a
    generated unique field collided with a row already persisted from
    a previous run, which is only detectable synchronously.
    """

    def __init__(self, connection: Connection, flush_threshold: int) -> None:
        self._connection = connection
        self._flush_threshold = flush_threshold
        self._rows: dict[str, list[tuple]] = {}
        self._columns: dict[str, tuple[str, ...]] = {}
        self._pending = 0

    def add(self, table: str, columns: tuple[str, ...], values: tuple) -> None:
        if table not in self._rows:
            self._rows[table] = []
            self._columns[table] = columns

        self._rows[table].append(values)
        self._pending += 1

        if self._pending >= self._flush_threshold:
            self.flush()

    def flush(self) -> None:
        if self._pending == 0:
            return

        with self._connection.cursor() as cursor:
            for table, rows in self._rows.items():
                if not rows:
                    continue

                cursor.execute(
                    self._build_insert(table, self._columns[table], len(rows)),
                    [value for row in rows for value in row],
                )

                rows.clear()

        self._connection.commit()

        self._pending = 0

    @staticmethod
    def _build_insert(
        table: str,
        columns: tuple[str, ...],
        row_count: int,
    ) -> str:
        column_list = ", ".join(columns)
        placeholder_group = "(" + ", ".join(["%s"] * len(columns)) + ")"
        values_clause = ", ".join([placeholder_group] * row_count)

        return (
            f"INSERT INTO {table} ({column_list}) "
            f"VALUES {values_clause} "
            "ON CONFLICT DO NOTHING"
        )
