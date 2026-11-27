"""Configuration loader for PostgreSQL connection and migration parameters."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

DEFAULT_OSM_TABLES: tuple[str, ...] = (
    "planet_osm_point",
    "planet_osm_line",
    "planet_osm_polygon",
    "planet_osm_roads",
)


@dataclass(frozen=True)
class DatabaseConfig:
    """PostgreSQL connection settings read from environment variables."""

    host: str
    port: int
    dbname: str
    user: str
    password: str


@dataclass(frozen=True)
class MigrationConfig:
    """Schema, threshold, and table settings for Bronze -> Silver -> Gold."""

    bronze_schema: str
    silver_schema: str
    gold_schema: str
    null_threshold_pct: float
    tables: tuple[str, ...] = DEFAULT_OSM_TABLES
    tags_column: str = "tags"


def load_configs(
    env_path: str | Path | None = None,
    threshold_override: float | None = None,
    tables_override: list[str] | None = None,
) -> tuple[DatabaseConfig, MigrationConfig]:
    """Load database and migration configuration from `.env` and environment."""
    if env_path is None:
        env_path = Path.cwd() / ".env"
    load_dotenv(dotenv_path=env_path, override=False)

    required = ("PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD")
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise RuntimeError(
            f"Missing required database environment variables: {', '.join(missing)}. "
            "Configure them in .env or the shell environment."
        )

    db_cfg = DatabaseConfig(
        host=os.environ["PGHOST"],
        port=int(os.environ["PGPORT"]),
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
    )

    threshold = (
        threshold_override
        if threshold_override is not None
        else float(os.environ.get("NULL_THRESHOLD_PCT", "40.0"))
    )
    tables = tuple(tables_override) if tables_override else DEFAULT_OSM_TABLES

    mig_cfg = MigrationConfig(
        bronze_schema=os.environ.get("BRONZE_SCHEMA", "public"),
        silver_schema=os.environ.get("SILVER_SCHEMA", "silver_jsonb"),
        gold_schema=os.environ.get("GOLD_SCHEMA", "gold_jsonb"),
        null_threshold_pct=threshold,
        tables=tables,
    )
    return db_cfg, mig_cfg
