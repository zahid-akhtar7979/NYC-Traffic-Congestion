"""
Database connection utilities for PostgreSQL and MySQL.
Uses Docker service names (postgres, mysql) for connectivity.
"""
import psycopg2
import mysql.connector
from typing import Optional


# PostgreSQL configuration
POSTGRES_CONFIG = {
    "host": "postgres",
    "database": "benchmark_pg",
    "user": "postgres",
    "password": "postgres",
    "port": 5432,
}


# MySQL configuration
MYSQL_CONFIG = {
    "host": "mysql",
    "database": "benchmark_mysql",
    "user": "root",
    "password": "root",
    "port": 3306,
}


def get_postgres_connection():
    """Return a new PostgreSQL connection."""
    return psycopg2.connect(**POSTGRES_CONFIG)


def get_mysql_connection():
    """Return a new MySQL connection."""
    return mysql.connector.connect(**MYSQL_CONFIG)
