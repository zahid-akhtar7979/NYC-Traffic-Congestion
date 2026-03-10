#!/usr/bin/env bash
# Bring up NYC Traffic Congestion: DBs, schema, data load, UI.
# Run from project root: ./scripts/run_full_stack.sh

set -e
cd "$(dirname "$0")/.."
COMPOSE="docker compose -f docker/docker-compose.yml"
PROJECT_ROOT="$(pwd)"

echo "=== 1. Starting PostgreSQL, MySQL, and App (Streamlit) ==="
$COMPOSE up --build -d
echo "Waiting for databases to be healthy..."
sleep 15
until $COMPOSE exec -T postgres pg_isready -U postgres 2>/dev/null; do echo "Waiting for PostgreSQL..."; sleep 2; done
until $COMPOSE exec -T mysql mysqladmin ping -h localhost -uroot -proot 2>/dev/null; do echo "Waiting for MySQL..."; sleep 2; done
echo "Databases are ready."

echo ""
echo "=== 2. Applying database schemas ==="
cat database/postgres_schema.sql | $COMPOSE exec -T postgres psql -U postgres -d benchmark_pg -q
echo "PostgreSQL schema applied."
cat database/mysql_schema.sql | $COMPOSE exec -T mysql mysql -u root -proot benchmark_mysql
echo "MySQL schema applied."

echo ""
echo "=== 3. Loading data (~1M CRZ, ~100K ridership) ==="
$COMPOSE run --rm app python data_loader/load_data.py
echo "Data load complete."

echo ""
echo "=== 4. UI and metrics ==="
echo "Streamlit dashboard is running at: http://localhost:8501"
echo "Open the URL to view Database Overview, run benchmarks, and see metrics."
echo ""
echo "To stop: docker compose -f docker/docker-compose.yml down"
