#!/bin/sh

# Copyright 2026 Ian Brooks
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Start Neo4j, seed the demo graph, then serve the browser.
set -eu
cd "$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
export NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
export NEO4J_USER="${NEO4J_USER:-neo4j}"
export NEO4J_PASSWORD="${NEO4J_PASSWORD:-cyber-semantic-layer}"
export NEO4J_REQUIRED="${NEO4J_REQUIRED:-1}"
docker compose -f deploy/docker-compose.yml -p cyber-semantic-layer up -d
python3 1_job-build-catalog/job.py
exec python3 2_app-browse-catalog/app.py
