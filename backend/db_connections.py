"""
Database connection utilities for PostgreSQL and MySQL.
Supports Docker (hosts postgres/mysql) and Railway (env vars DATABASE_URL, MYSQL_*).
"""
import os
import psycopg2
import mysql.connector
from typing import Optional


def _get_postgres_config():
    """PostgreSQL config: Railway DATABASE_URL or PG* env vars, else Docker defaults."""
    url = os.environ.get("DATABASE_URL")
    if url:
        return {"conn_str": url}
    return {
        "host": os.environ.get("PGHOST", "postgres"),
        "database": os.environ.get("PGDATABASE", "benchmark_pg"),
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", "postgres"),
        "port": int(os.environ.get("PGPORT", "5432")),
    }


def _get_mysql_config():
    """MySQL config: Railway MYSQL_* / MYSQL* env vars, else Docker defaults."""
    host = os.environ.get("MYSQLHOST") or os.environ.get("MYSQL_HOST", "mysql")
    port = int(os.environ.get("MYSQLPORT") or os.environ.get("MYSQL_PORT", "3306"))
    user = os.environ.get("MYSQLUSER") or os.environ.get("MYSQL_USER", "root")
    password = os.environ.get("MYSQLPASSWORD") or os.environ.get("MYSQL_PASSWORD", "root")
    database = os.environ.get("MYSQLDATABASE") or os.environ.get("MYSQL_DATABASE", "benchmark_mysql")
    return {"host": host, "port": port, "user": user, "password": password, "database": database}


def get_postgres_connection():
    """Return a new PostgreSQL connection."""
    cfg = _get_postgres_config()
    if "conn_str" in cfg:
        return psycopg2.connect(cfg["conn_str"])
    return psycopg2.connect(
        host=cfg["host"],
        database=cfg["database"],
        user=cfg["user"],
        password=cfg["password"],
        port=cfg["port"],
    )


def get_mysql_connection():
    """Return a new MySQL connection."""
    cfg = _get_mysql_config()
    return mysql.connector.connect(**cfg)
