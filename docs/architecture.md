# Architecture

Cloudera Machine Learning is the launch target. Neo4j holds the posture graph. The semantic model that binds questions to that graph is described in [Semantic knowledge layer](semantic-knowledge-layer.md).

```text
0_session-install-dependencies
        |
        v
1_job-build-catalog
        |
        +--> assets/data/catalog.json
        |
        +--> Neo4j  (shadow-admin subgraph)
                    |
                    v
             2_app-browse-catalog
             match question -> guessed walk and Ossie path
```

| Piece | Role |
| --- | --- |
| `src/cyber_semantic_layer` | Catalog model, sample catalog, JSON snapshot, Neo4j seed, and question bindings |
| `0_session-install-dependencies` | Installs the package into the CML session |
| `1_job-build-catalog` | Writes the catalog snapshot and, when `NEO4J_URI` is set, seeds Neo4j |
| `2_app-browse-catalog` | Serves the question form and the posture comparison |
| `deploy/docker-compose.yml` | Local Neo4j 5. Browser on port 7474, Bolt on port 7687 |
| `deploy/run-local.sh` | Starts Neo4j, runs the job, then serves the application |
| `.project-metadata.yaml` | CML runbook that orders the session, job, and application |
| `METADATA.yaml` | Fields for the Cloudera blueprint website |
| `catalog-entry.yaml` | Entry for a custom CML AMP catalog |

## Request path

The application listens on `CDSW_APP_PORT` inside CML. Locally it listens on port 8080. `PORT` overrides both.

A GET or POST to `/` with a `question` parameter is matched in `prepare_question`. A match runs two Cypher queries and the path queries that draw the graphs. Unmatched text returns no answer. When `NEO4J_URI` is unset, or Neo4j is unreachable, the page keeps the match and reports that the query did not run.

The posture table under the form runs the four default questions the same way.

## Configuration

| Variable | Default | Used for |
| --- | --- | --- |
| `CATALOG_PATH` | `assets/data/catalog.json` | Snapshot path, relative to the repository root |
| `NEO4J_URI` | unset in the app; `bolt://localhost:7687` in `run-local.sh` | Seed and queries. The app skips Neo4j when this is unset |
| `NEO4J_USER` | `neo4j` | Bolt user |
| `NEO4J_PASSWORD` | `cyber-semantic-layer` | Bolt password. Replace this outside the local demo |
| `PORT` | | Local listen port |
| `CDSW_APP_PORT` | | Listen port inside CML |

The seed retries for about a minute so the job can start while Neo4j is still opening Bolt.
