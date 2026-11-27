"""Reporting utilities to output SQL artifacts, JSON metrics, and Markdown summaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .inspector import TableClassification
from .silver_migrator import TableMigrationResult, build_silver_sql


def write_silver_sql_file(
    output_path: Path,
    classifications: dict[str, TableClassification],
    tags_column: str = "tags",
) -> None:
    """Write the dynamically generated Silver-layer DDL & DML SQL to a file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sections = ["-- Auto-generated Silver-layer JSONB migration SQL"]
    first_schema = next(iter(classifications.values())).silver_schema
    sections.append(f'CREATE SCHEMA IF NOT EXISTS "{first_schema}";\n')

    for tbl_name, cls in classifications.items():
        create_sql, insert_sql, index_sqls = build_silver_sql(cls, tags_column=tags_column)
        sections.append(f"-- === {cls.silver_schema}.{tbl_name} ===")
        sections.append(create_sql)
        sections.append(insert_sql)
        sections.extend(index_sqls)
        sections.append(f'ANALYZE "{cls.silver_schema}"."{tbl_name}";\n')

    output_path.write_text("\n\n".join(sections) + "\n", encoding="utf-8")


def write_reports(
    report_dir: Path,
    classifications: dict[str, TableClassification],
    migration_results: dict[str, TableMigrationResult] | None,
    gold_checks: list[dict[str, Any]] | None,
) -> tuple[Path, Path]:
    """Write machine-readable JSON and human-readable Markdown migration reports."""
    report_dir.mkdir(parents=True, exist_ok=True)

    json_payload: dict[str, Any] = {"tables": {}, "gold_verification": gold_checks or []}
    md_lines: list[str] = [
        "# OSM Bronze → Silver (JSONB) → Gold Migration Report\n",
    ]

    for tbl_name, cls in classifications.items():
        mig = migration_results.get(tbl_name) if migration_results else None
        json_payload["tables"][tbl_name] = {
            "bronze_schema": cls.bronze_schema,
            "silver_schema": cls.silver_schema,
            "total_rows": cls.total_rows,
            "threshold_pct": cls.threshold_pct,
            "independent_columns": [c.name for c in cls.independent_columns],
            "jsonb_columns": [c.name for c in cls.jsonb_columns],
            "columns": [
                {
                    "name": c.name,
                    "pg_type": c.pg_type,
                    "null_count": c.null_count,
                    "null_pct": round(c.null_pct, 4),
                    "is_structural": c.is_structural,
                    "classification": c.classification,
                    "reason": c.reason,
                }
                for c in cls.columns
            ],
            "migration": (
                {
                    "bronze_rows": mig.bronze_rows,
                    "silver_rows": mig.silver_rows,
                    "null_values_in_tags": mig.null_values_in_tags,
                    "leaked_independent_keys": mig.leaked_independent_keys,
                    "empty_tags_rows": mig.empty_tags_rows,
                    "non_empty_tags_rows": mig.non_empty_tags_rows,
                    "duration_seconds": mig.duration_seconds,
                    "passed": mig.passed,
                }
                if mig
                else None
            ),
        }

        md_lines.append(f"## `{cls.bronze_schema}.{tbl_name}` → `{cls.silver_schema}.{tbl_name}`\n")
        md_lines.append(
            f"- **Total rows:** {cls.total_rows:,}\n"
            f"- **Threshold:** NULL % < {cls.threshold_pct:.1f}% → independent column; "
            f"NULL % >= {cls.threshold_pct:.1f}% → `tags` JSONB\n"
            f"- **Independent columns ({len(cls.independent_columns)}):** "
            + ", ".join(f"`{c.name}` (`{c.pg_type}`, {c.null_pct:.2f}% NULL)" for c in cls.independent_columns)
            + f"\n- **JSONB `tags` attributes:** {len(cls.jsonb_columns)} columns\n"
        )
        if mig:
            md_lines.append(
                f"- **Migration verification:** `bronze={mig.bronze_rows:,}`, "
                f"`silver={mig.silver_rows:,}`, `nulls_in_tags={mig.null_values_in_tags}`, "
                f"`leaked_keys={mig.leaked_independent_keys}`, "
                f"`empty_tags={mig.empty_tags_rows:,}`, `non_empty_tags={mig.non_empty_tags_rows:,}`, "
                f"`duration={mig.duration_seconds}s`, **passed={mig.passed}**\n"
            )

        md_lines.append("\n| Column | PostgreSQL Type | NULL Count | NULL % | Classification | Rule |")
        md_lines.append("|---|---|---:|---:|---|---|")
        for c in cls.columns:
            md_lines.append(
                f"| `{c.name}` | `{c.pg_type}` | {c.null_count:,} | {c.null_pct:.2f}% | `{c.classification}` | {c.reason} |"
            )
        md_lines.append("")

    if gold_checks:
        md_lines.append("## Gold Layer Equivalence Verification\n")
        md_lines.append("| Gold Object | Gold Rows | Expected (Bronze) Rows | Match |")
        md_lines.append("|---|---:|---:|:---:|")
        for chk in gold_checks:
            md_lines.append(
                f"| `{chk['object']}` | {chk['gold_count']:,} | {chk['expected_bronze_count']:,} | "
                + ("PASS" if chk["match"] else "FAIL")
                + " |"
            )
            if "aggregates" in chk:
                agg = chk["aggregates"]
                md_lines.append(
                    f"\nGrid statistics totals: attractions={agg['sum_total_attractions']:,}, "
                    f"accommodations={agg['sum_total_accommodations']:,}, "
                    f"restaurants={agg['sum_total_restaurants']:,}.\n"
                )

    json_path = report_dir / "migration_report.json"
    md_path = report_dir / "migration_report.md"
    json_path.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return json_path, md_path
