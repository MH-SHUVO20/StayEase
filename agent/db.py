"""Small PostgreSQL helper functions for StayEase tools."""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv()


def _json_ready(value: Any) -> Any:
    """Convert PostgreSQL values into JSON-friendly Python values."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    return value


def _clean_row(row: dict[str, Any]) -> dict[str, Any]:
    """Convert one database row into a JSON-friendly dictionary."""
    return {key: _json_ready(value) for key, value in row.items()}


def get_database_url() -> str:
    """Return the configured PostgreSQL connection string."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")
    return database_url


@contextmanager
def get_connection() -> Iterator[Any]:
    """Open a PostgreSQL connection and close it after use."""
    connection = psycopg2.connect(get_database_url())
    try:
        yield connection
    finally:
        connection.close()


def fetch_all(query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    """Run a SELECT query and return rows as dictionaries."""
    with get_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            return [_clean_row(dict(row)) for row in cursor.fetchall()]


def fetch_one(query: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
    """Run a SELECT query and return one row as a dictionary."""
    with get_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()
            return _clean_row(dict(row)) if row else None


def execute_one(query: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
    """Run an INSERT/UPDATE query with RETURNING and commit it."""
    with get_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()
            connection.commit()
            return _clean_row(dict(row)) if row else None
