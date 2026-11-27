"""CLI entry point for dynamic OSM Bronze -> Silver (JSONB) -> Gold migration."""

from __future__ import annotations

import argparse
from pathlib import Path

from osm_warehouse.config import load_configs
from osm_warehouse.db import get_connection
from osm_warehouse.gold_generator import (
    build_gold_sql,
    deploy_gold_layer,
    verify_gold_equivalence,
)
from osm_warehouse.inspector import inspect_all_tables
from osm_warehouse.reporter import write_reports, write_silver_sql_file
from osm_warehouse.silver_migrator import migrate_silver_table


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dynamically redesign OSM Bronze tables into Silver JSONB and update Gold DDL."
    )
    parser.add_argument(
        "--env",
        default=".env",
        help="Path to .env file with database credentials (default: .env).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="NULL percentage threshold (default from NULL_THRESHOLD_PCT or 40.0).",
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        default=None,
        help="Optional subset of Bronze tables to process.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect, classify, and generate SQL/reports without modifying the database.",
    )
    parser.add_argument(
        "--skip-gold",
        action="store_true",
        help="Only migrate Silver tables; skip deploying Gold views/tables.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_cfg, mig_cfg = load_configs(
        env_path=args.env,
        threshold_override=args.threshold,
        tables_override=args.tables,
    )

    root = Path.cwd()
    sql_dir = root / "sql"
    report_dir = root / "reports"

    with get_connection(db_cfg) as conn:
        print(
            f"Connected to {db_cfg.dbname} on {db_cfg.host}:{db_cfg.port} "
            f"(Bronze={mig_cfg.bronze_schema}, Silver={mig_cfg.silver_schema}, "
            f"Gold={mig_cfg.gold_schema}, Threshold={mig_cfg.null_threshold_pct:.1f}%)"
        )

        # 1. Inspect and classify all Bronze tables dynamically
        classifications = inspect_all_tables(
            conn=conn,
            bronze_schema=mig_cfg.bronze_schema,
            silver_schema=mig_cfg.silver_schema,
            tables=mig_cfg.tables,
            threshold_pct=mig_cfg.null_threshold_pct,
        )

        for tbl_name, cls in classifications.items():
            indep = [c.name for c in cls.independent_columns]
            print(
                f"[{tbl_name}] rows={cls.total_rows:,} | "
                f"independent ({len(indep)}): {indep} | "
                f"jsonb tags cols: {len(cls.jsonb_columns)}"
            )

        # Write generated Silver & Gold SQL artifacts
        silver_sql_path = sql_dir / f"{mig_cfg.silver_schema}.sql"
        write_silver_sql_file(silver_sql_path, classifications, tags_column=mig_cfg.tags_column)
        print(f"Generated Silver SQL: {silver_sql_path}")

        gold_sql = build_gold_sql(
            classifications=classifications,
            gold_schema=mig_cfg.gold_schema,
            tags_column=mig_cfg.tags_column,
        )
        gold_sql_path = sql_dir / f"{mig_cfg.gold_schema}.sql"
        gold_sql_path.parent.mkdir(parents=True, exist_ok=True)
        gold_sql_path.write_text(gold_sql, encoding="utf-8")
        print(f"Generated Gold SQL:   {gold_sql_path}")

        if args.dry_run:
            json_path, md_path = write_reports(report_dir, classifications, None, None)
            print(f"Dry-run complete. Reports written to {json_path} and {md_path}")
            return

        # 2. Migrate each Silver table dynamically
        migration_results = {}
        for tbl_name, cls in classifications.items():
            print(f"Migrating {cls.bronze_schema}.{tbl_name} -> {cls.silver_schema}.{tbl_name} ...")
            res = migrate_silver_table(conn, cls, tags_column=mig_cfg.tags_column)
            migration_results[tbl_name] = res
            print(
                f"  Done in {res.duration_seconds}s | rows={res.silver_rows:,}/{res.bronze_rows:,} | "
                f"nulls_in_tags={res.null_values_in_tags} | leaked={res.leaked_independent_keys} | "
                f"non_empty_tags={res.non_empty_tags_rows:,} | passed={res.passed}"
            )
            if not res.passed:
                raise RuntimeError(f"Verification failed for {cls.silver_schema}.{tbl_name}!")

        # 3. Deploy and verify Gold layer
        gold_checks = None
        if not args.skip_gold:
            print(f"Deploying Gold schema '{mig_cfg.gold_schema}' ...")
            deploy_gold_layer(conn, gold_sql)
            gold_checks = verify_gold_equivalence(
                conn=conn,
                bronze_schema=mig_cfg.bronze_schema,
                gold_schema=mig_cfg.gold_schema,
            )
            for chk in gold_checks:
                status = "PASS" if chk["match"] else "FAIL"
                print(
                    f"  [{status}] {chk['object']}: gold={chk['gold_count']:,} "
                    f"(expected={chk['expected_bronze_count']:,})"
                )
                if not chk["match"]:
                    raise RuntimeError(f"Gold equivalence check failed for {chk['object']}!")

        json_path, md_path = write_reports(report_dir, classifications, migration_results, gold_checks)
        print(f"Migration complete! Reports saved to {json_path} and {md_path}")


if __name__ == "__main__":
    main()
