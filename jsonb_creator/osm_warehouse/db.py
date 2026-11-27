"""Database connection and SQL formatting utilities."""

from __future__ import annotations

import psycopg
from .config import DatabaseConfig


def get_connection(cfg: DatabaseConfig) -> psycopg.Connection:
    """Open a PostgreSQL connection using explicit parameters."""
    return psycopg.connect(
        host=cfg.host,
        port=cfg.port,
        dbname=cfg.dbname,
        user=cfg.user,
        password=cfg.password,
    )


def quote_ident(identifier: str) -> str:
    """Safely double-quote a PostgreSQL identifier for readable SQL output."""
    return '"' + identifier.replace('"', '""') + '"'


def quote_literal(value: str) -> str:
    """Safely single-quote a PostgreSQL string literal for readable SQL output."""
    return "'" + value.replace("'", "''") + "'"
