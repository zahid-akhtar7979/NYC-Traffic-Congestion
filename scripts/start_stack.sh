#!/usr/bin/env bash
# Start existing Docker stack for NYC Traffic Congestion WITHOUT reapplying schema or reloading data.
# Use after you have run ./scripts/init_db_and_data.sh once.
#
# Run from project root: ./scripts/start_stack.sh

set -e
cd "$(dirname "$0")/.."

echo "Starting Docker services (postgres, mysql, app)..."
docker compose -f docker/docker-compose.yml up -d

echo ""
echo "Dashboard should be available at: http://localhost:8501"
echo "To stop: docker compose -f docker/docker-compose.yml down"

