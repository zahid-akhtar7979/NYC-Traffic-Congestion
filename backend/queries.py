"""
Benchmark query definitions for NYC Congestion Pricing Analytics.
All queries use the star schema (Fact_CRZ_Entries and dimensions).
"""

# Aggregation Query
QUERY_AGGREGATION = """
SELECT vehicle_class_id, SUM(entry_count)
FROM Fact_CRZ_Entries
GROUP BY vehicle_class_id
"""

# Join Query
QUERY_JOIN = """
SELECT d.year, vc.vehicle_class_name, SUM(f.entry_count)
FROM Fact_CRZ_Entries f
JOIN Dim_Date d ON f.date_id = d.date_id
JOIN Dim_Vehicle_Class vc ON f.vehicle_class_id = vc.vehicle_class_id
GROUP BY d.year, vc.vehicle_class_name
"""

# Date Filter Query
QUERY_DATE_FILTER = """
SELECT *
FROM Fact_CRZ_Entries
WHERE date_id BETWEEN 20240101 AND 20240131
"""

# Index Lookup Query
QUERY_INDEX_LOOKUP = """
SELECT *
FROM Fact_CRZ_Entries
WHERE vehicle_class_id = 1
"""

# All benchmark queries for iteration
BENCHMARK_QUERIES = {
    "aggregation": QUERY_AGGREGATION,
    "join": QUERY_JOIN,
    "date_filter": QUERY_DATE_FILTER,
    "index_lookup": QUERY_INDEX_LOOKUP,
}
