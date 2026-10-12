#!/bin/sh
# Start Neo4j, seed the demo graph, then serve the browser.
set -eu
cd "$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
export NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
export NEO4J_USER="${NEO4J_USER:-neo4j}"
export NEO4J_PASSWORD="${NEO4J_PASSWORD:-cyber-semantic-layer}"
docker compose -f deploy/docker-compose.yml -p cyber-semantic-layer up -d
python3 1_job-build-catalog/job.py
exec python3 2_app-browse-catalog/app.py
