"""
Data loader for NYC Congestion Pricing Analytics.
Loads dimension and fact data into PostgreSQL and MySQL.
Run after schema has been applied.
"""
import os
import sys

# Allow importing backend when run from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db_connections import get_postgres_connection, get_mysql_connection


def load_dimension_seed_pg(conn):
    """Insert minimal seed data into dimension tables (PostgreSQL) for benchmarking."""
    cur = conn.cursor()
    # Dim_Date
    cur.execute(
        "INSERT INTO Dim_Date (date_id, full_date, year, month, day, day_of_week) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (date_id) DO NOTHING",
        (20240101, "2024-01-01", 2024, 1, 1, "Monday"),
    )
    cur.execute(
        "INSERT INTO Dim_Date (date_id, full_date, year, month, day, day_of_week) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (date_id) DO NOTHING",
        (20240115, "2024-01-15", 2024, 1, 15, "Monday"),
    )
    # Dim_Time
    cur.execute(
        "INSERT INTO Dim_Time (time_id, hour, minute, time_period) VALUES (%s, %s, %s, %s) ON CONFLICT (time_id) DO NOTHING",
        (1, 8, 0, "AM Peak"),
    )
    # Dim_Location
    cur.execute(
        "INSERT INTO Dim_Location (location_id, borough, street_name, intersection, latitude, longitude) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (location_id) DO NOTHING",
        (1, "Manhattan", "5th Ave", "34th St", 40.7484, -73.9857),
    )
    # Dim_Vehicle_Class
    for i, name in enumerate(["Passenger", "Truck", "Motorcycle"], start=1):
        cur.execute(
            "INSERT INTO Dim_Vehicle_Class (vehicle_class_id, vehicle_class_name) VALUES (%s, %s) ON CONFLICT (vehicle_class_id) DO NOTHING",
            (i, name),
        )
    conn.commit()
    cur.close()


def load_dimension_seed_mysql(conn):
    """Insert minimal seed data into dimension tables (MySQL) for benchmarking."""
    cur = conn.cursor()
    cur.execute(
        "INSERT IGNORE INTO Dim_Date (date_id, full_date, year, month, day, day_of_week) VALUES (20240101, '2024-01-01', 2024, 1, 1, 'Monday')"
    )
    cur.execute(
        "INSERT IGNORE INTO Dim_Date (date_id, full_date, year, month, day, day_of_week) VALUES (20240115, '2024-01-15', 2024, 1, 15, 'Monday')"
    )
    cur.execute(
        "INSERT IGNORE INTO Dim_Time (time_id, hour, minute, time_period) VALUES (1, 8, 0, 'AM Peak')"
    )
    cur.execute(
        "INSERT IGNORE INTO Dim_Location (location_id, borough, street_name, intersection, latitude, longitude) VALUES (1, 'Manhattan', '5th Ave', '34th St', 40.7484, -73.9857)"
    )
    for i, name in enumerate(["Passenger", "Truck", "Motorcycle"], start=1):
        cur.execute(
            "INSERT IGNORE INTO Dim_Vehicle_Class (vehicle_class_id, vehicle_class_name) VALUES (%s, %s)",
            (i, name),
        )
    conn.commit()
    cur.close()


def load_fact_seed_pg(conn, num_rows: int = 1000):
    """Insert sample fact rows into Fact_CRZ_Entries (PostgreSQL)."""
    cur = conn.cursor()
    for i in range(num_rows):
        date_id = 20240101 if i % 2 == 0 else 20240115
        cur.execute(
            "INSERT INTO Fact_CRZ_Entries (crz_entry_id, date_id, time_id, location_id, vehicle_class_id, entry_count) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (crz_entry_id) DO NOTHING",
            (i + 1, date_id, 1, 1, (i % 3) + 1, 1 + (i % 10)),
        )
    conn.commit()
    cur.close()


def load_fact_seed_mysql(conn, num_rows: int = 1000):
    """Insert sample fact rows into Fact_CRZ_Entries (MySQL)."""
    cur = conn.cursor()
    for i in range(num_rows):
        date_id = 20240101 if i % 2 == 0 else 20240115
        cur.execute(
            "INSERT IGNORE INTO Fact_CRZ_Entries (crz_entry_id, date_id, time_id, location_id, vehicle_class_id, entry_count) VALUES (%s, %s, %s, %s, %s, %s)",
            (i + 1, date_id, 1, 1, (i % 3) + 1, 1 + (i % 10)),
        )
    conn.commit()
    cur.close()


def load_all(num_fact_rows: int = 1000):
    """Load seed dimensions and fact data into both databases."""
    pg = get_postgres_connection()
    mysql = get_mysql_connection()
    try:
        load_dimension_seed_pg(pg)
        load_dimension_seed_mysql(mysql)
        load_fact_seed_pg(pg, num_fact_rows)
        load_fact_seed_mysql(mysql, num_fact_rows)
        print("Seed data loaded into PostgreSQL and MySQL.")
    finally:
        pg.close()
        mysql.close()


if __name__ == "__main__":
    load_all(num_fact_rows=1000)
