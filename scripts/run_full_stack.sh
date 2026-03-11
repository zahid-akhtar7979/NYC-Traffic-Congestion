#!/usr/bin/env bash
# Legacy helper: full one-shot setup (build, schema, data, start UI).
# Kept for convenience; for clearer control prefer:
#   - ./scripts/init_db_and_data.sh  (one-time)
#   - ./scripts/start_stack.sh       (subsequent runs)

set -e
cd "$(dirname "$0")/.."

echo "Running full initialization (build + schema + data load)..."
./scripts/init_db_and_data.sh
