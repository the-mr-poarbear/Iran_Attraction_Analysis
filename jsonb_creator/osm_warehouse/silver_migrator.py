"""Dynamic Silver-layer table DDL generation, migration, indexing, and verification."""

from __future__ import annotations

import time
from dataclasses import dataclass
import psycopg

from .db import quote_ident, quote_literal
from .inspector import TableClassification


@dataclass
class TableMigrationResult:
    """Execution metrics and verification results for one migrated Silver table."""

    table_name: str
    bronze_rows: int
    silver_rows: int
    independent_col_count: int
    jsonb_col_count: int
    null_values_in_tags: int
    leaked_independent_keys: int
    empty_tags_rows: int
    non_empty_tags_rows: int
    duration_seconds: float
    create_sql: str
    insert_sql: str
    index_sqls: list[str]

    @property
    def passed(self) -> bool:
        return (
            self.bronze_rows == self.silver_rows
            and self.null_values_in_tags == 0
            and self.leaked_independent_keys == 0
        )


def build_silver_sql(
    cls: TableClassification,
    tags_column: str = "tags",
) -> tuple[str, str, list[str]]:
    """Generate CREATE TABLE, INSERT ... SELECT, and CREATE INDEX SQL dynamically."""
    schema_q = quote_ident(cls.silver_schema)
    table_q = quote_ident(cls.table_name)
    bronze_schema_q = quote_ident(cls.bronze_schema)
    tags_q = quote_ident(tags_column)

    col_defs = [
        f"    {quote_ident(col.name)} {col.pg_type}"
        for col in cls.independent_columns
    ]
    col_defs.append(f"    {tags_q} jsonb NOT NULL DEFAULT '{{}}'::jsonb")

    create_sql = (
        f"DROP TABLE IF EXISTS {schema_q}.{table_q} CASCADE;\n"
        f"CREATE TABLE {schema_q}.{table_q} (\n"
        + ",\n".join(col_defs)
        + "\n);"
    )

    indep_names = [col.name for col in cls.independent_columns]
    target_cols_sql = ", ".join([quote_ident(n) for n in indep_names] + [tags_q])
    select_indep_sql = ",\n    ".join(f"src.{quote_ident(n)}" for n in indep_names)

    if cls.jsonb_columns:
        excluded_array = ", ".join(quote_literal(n) for n in indep_names)
        tags_expr = (
            f"COALESCE(\n"
            f"        jsonb_strip_nulls(\n"
            f"            to_jsonb(src) - ARRAY[{excluded_array}]::text[]\n"
            f"        ),\n"
            f"        '{{}}'::jsonb\n"
            f"    ) AS {tags_q}"
        )
    else:
        tags_expr = f"'{{}}'::jsonb AS {tags_q}"

    insert_sql = (
        f"INSERT INTO {schema_q}.{table_q} ({target_cols_sql})\n"
        f"SELECT\n"
        f"    {select_indep_sql},\n"
        f"    {tags_expr}\n"
        f"FROM {bronze_schema_q}.{table_q} AS src;"
    )

    index_sqls: list[str] = []
    for geom_col in cls.geometry_columns:
        idx_name = quote_ident(f"idx_{cls.table_name}_{geom_col.name}_gist")
        index_sqls.append(
            f"CREATE INDEX {idx_name} ON {schema_q}.{table_q} "
            f"USING GIST ({quote_ident(geom_col.name)});"
        )

    gin_idx = quote_ident(f"idx_{cls.table_name}_{tags_column}_gin")
    index_sqls.append(
        f"CREATE INDEX {gin_idx} ON {schema_q}.{table_q} "
        f"USING GIN ({tags_q});"
    )

    if cls.get_column("osm_id") is not None:
        id_idx = quote_ident(f"idx_{cls.table_name}_osm_id")
        index_sqls.append(
            f"CREATE INDEX {id_idx} ON {schema_q}.{table_q} ({quote_ident('osm_id')});"
        )

    return create_sql, insert_sql, index_sqls


def migrate_silver_table(
    conn: psycopg.Connection,
    cls: TableClassification,
    tags_column: str = "tags",
) -> TableMigrationResult:
    """Create Silver table, transfer data with stripped JSONB tags, index, and verify."""
    t0 = time.perf_counter()
    create_sql, insert_sql, index_sqls = build_silver_sql(cls, tags_column=tags_column)
    schema_q = quote_ident(cls.silver_schema)
    table_q = quote_ident(cls.table_name)
    tags_q = quote_ident(tags_column)

    with conn.cursor() as cur:
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_q};")
        cur.execute(create_sql)
        cur.execute(insert_sql)
        for idx_sql in index_sqls:
            cur.execute(idx_sql)
        cur.execute(f"ANALYZE {schema_q}.{table_q};")
    conn.commit()

    # Verify data integrity
    indep_names = [col.name for col in cls.independent_columns]
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT
                COUNT(*) AS total_rows,
                COUNT(*) FILTER (WHERE {tags_q} = '{{}}'::jsonb) AS empty_tags,
                COUNT(*) FILTER (WHERE {tags_q} <> '{{}}'::jsonb) AS non_empty_tags,
                COUNT(*) FILTER (WHERE {tags_q} ?| %s::text[]) AS leaked_keys
            FROM {schema_q}.{table_q}
            """,
            (indep_names,),
        )
        silver_rows, empty_tags, non_empty_tags, leaked_keys = cur.fetchone()

        cur.execute(
            f"""
            SELECT COUNT(*)
            FROM {schema_q}.{table_q} t
            WHERE EXISTS (
                SELECT 1
                FROM jsonb_each(t.{tags_q}) AS kv(k, v)
                WHERE jsonb_typeof(kv.v) = 'null'
            )
            """
        )
        null_in_tags = int(cur.fetchone()[0])

    duration = time.perf_counter() - t0
    return TableMigrationResult(
        table_name=cls.table_name,
        bronze_rows=cls.total_rows,
        silver_rows=int(silver_rows),
        independent_col_count=len(cls.independent_columns),
        jsonb_col_count=len(cls.jsonb_columns),
        null_values_in_tags=null_in_tags,
        leaked_independent_keys=int(leaked_keys),
        empty_tags_rows=int(empty_tags),
        non_empty_tags_rows=int(non_empty_tags),
        duration_seconds=round(duration, 2),
        create_sql=create_sql,
        insert_sql=insert_sql,
        index_sqls=index_sqls,
    )
