"""Dynamic schema inspection and NULL-percentage column classification."""

from __future__ import annotations

from dataclasses import dataclass, field
import psycopg
from psycopg import sql

STRUCTURAL_COLUMN_NAMES = frozenset({"osm_id"})
SPATIAL_UDT_NAMES = frozenset({"geometry", "geography"})


@dataclass(frozen=True)
class ColumnProfile:
    """Metadata, NULL statistics, and Silver classification for one source column."""

    name: str
    pg_type: str
    udt_name: str
    is_nullable: bool
    ordinal_position: int
    total_rows: int
    null_count: int
    non_null_count: int
    null_pct: float
    is_structural: bool
    classification: str  # "independent" or "jsonb"
    reason: str


@dataclass
class TableClassification:
    """Dynamic inspection and classification result for a single Bronze table."""

    bronze_schema: str
    silver_schema: str
    table_name: str
    total_rows: int
    threshold_pct: float
    columns: list[ColumnProfile] = field(default_factory=list)

    @property
    def independent_columns(self) -> list[ColumnProfile]:
        return [c for c in self.columns if c.classification == "independent"]

    @property
    def jsonb_columns(self) -> list[ColumnProfile]:
        return [c for c in self.columns if c.classification == "jsonb"]

    @property
    def geometry_columns(self) -> list[ColumnProfile]:
        return [c for c in self.independent_columns if c.udt_name in SPATIAL_UDT_NAMES]

    def get_column(self, col_name: str) -> ColumnProfile | None:
        for col in self.columns:
            if col.name == col_name:
                return col
        return None


def _fetch_table_columns(
    conn: psycopg.Connection,
    schema_name: str,
    table_name: str,
) -> list[tuple[str, str, str, bool, int]]:
    """Retrieve exact PostgreSQL column metadata dynamically from system catalogs."""
    query = """
        SELECT
            c.column_name,
            pg_catalog.format_type(a.atttypid, a.atttypmod) AS pg_type,
            c.udt_name,
            (c.is_nullable = 'YES') AS is_nullable,
            c.ordinal_position
        FROM information_schema.columns c
        JOIN pg_catalog.pg_namespace n
            ON n.nspname = c.table_schema
        JOIN pg_catalog.pg_class cl
            ON cl.relname = c.table_name
           AND cl.relnamespace = n.oid
        JOIN pg_catalog.pg_attribute a
            ON a.attrelid = cl.oid
           AND a.attname = c.column_name
        WHERE c.table_schema = %s
          AND c.table_name = %s
          AND a.attnum > 0
          AND NOT a.attisdropped
        ORDER BY c.ordinal_position
    """
    with conn.cursor() as cur:
        cur.execute(query, (schema_name, table_name))
        rows = cur.fetchall()
    if not rows:
        raise ValueError(f"Table {schema_name}.{table_name} does not exist or has no columns.")
    return rows


def inspect_table(
    conn: psycopg.Connection,
    bronze_schema: str,
    silver_schema: str,
    table_name: str,
    threshold_pct: float = 40.0,
) -> TableClassification:
    """Inspect a Bronze table, compute NULL percentages, and classify columns."""
    col_defs = _fetch_table_columns(conn, bronze_schema, table_name)

    agg_exprs = [sql.SQL("COUNT(*) AS __total_rows")]
    for col_name, _, _, _, _ in col_defs:
        agg_exprs.append(
            sql.SQL("COUNT(*) - COUNT({})").format(sql.Identifier(col_name))
        )

    stats_query = sql.SQL("SELECT {} FROM {}.{}").format(
        sql.SQL(", ").join(agg_exprs),
        sql.Identifier(bronze_schema),
        sql.Identifier(table_name),
    )

    with conn.cursor() as cur:
        cur.execute(stats_query)
        stats_row = cur.fetchone()

    total_rows = int(stats_row[0])
    profiles: list[ColumnProfile] = []

    for idx, (col_name, pg_type, udt_name, is_nullable, ordinal_pos) in enumerate(col_defs):
        null_count = int(stats_row[idx + 1])
        non_null_count = total_rows - null_count
        null_pct = (null_count * 100.0 / total_rows) if total_rows > 0 else 0.0
        is_structural = col_name in STRUCTURAL_COLUMN_NAMES or udt_name in SPATIAL_UDT_NAMES

        if is_structural:
            classification = "independent"
            reason = (
                "structural identifier"
                if col_name in STRUCTURAL_COLUMN_NAMES
                else f"structural spatial column ({udt_name})"
            )
        elif null_pct < threshold_pct:
            classification = "independent"
            reason = f"null_pct ({null_pct:.2f}%) < {threshold_pct:.1f}%"
        else:
            classification = "jsonb"
            reason = f"null_pct ({null_pct:.2f}%) >= {threshold_pct:.1f}%"

        profiles.append(
            ColumnProfile(
                name=col_name,
                pg_type=pg_type,
                udt_name=udt_name,
                is_nullable=is_nullable,
                ordinal_position=ordinal_pos,
                total_rows=total_rows,
                null_count=null_count,
                non_null_count=non_null_count,
                null_pct=null_pct,
                is_structural=is_structural,
                classification=classification,
                reason=reason,
            )
        )

    return TableClassification(
        bronze_schema=bronze_schema,
        silver_schema=silver_schema,
        table_name=table_name,
        total_rows=total_rows,
        threshold_pct=threshold_pct,
        columns=profiles,
    )


def inspect_all_tables(
    conn: psycopg.Connection,
    bronze_schema: str,
    silver_schema: str,
    tables: tuple[str, ...],
    threshold_pct: float = 40.0,
) -> dict[str, TableClassification]:
    """Independently inspect and classify all target Bronze tables."""
    results: dict[str, TableClassification] = {}
    for table_name in tables:
        results[table_name] = inspect_table(
            conn=conn,
            bronze_schema=bronze_schema,
            silver_schema=silver_schema,
            table_name=table_name,
            threshold_pct=threshold_pct,
        )
    return results
