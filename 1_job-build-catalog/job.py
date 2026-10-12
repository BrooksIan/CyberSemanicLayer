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

"""Write the sample semantic catalog and, when NEO4J_URI is set, seed Neo4j."""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cyber_semantic_layer.neo4j_graph import neo4j_enabled, open_driver, seed_demo
from cyber_semantic_layer.seed import build_sample_catalog
from cyber_semantic_layer.serialize import resolve_catalog_path, write_catalog


def write_sample_catalog(path: Path) -> Path:
    write_catalog(build_sample_catalog(), path)
    return path


def seed_neo4j(attempts: int = 30, pause_seconds: float = 2) -> None:
    if not neo4j_enabled():
        print("NEO4J_URI is unset. Skipped Neo4j seed.")
        return
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            driver = open_driver()
            try:
                seed_demo(driver)
            finally:
                driver.close()
            print("seeded Neo4j demo graph shadow-admin")
            return
        except Exception as exc:
            last_error = exc
            print(f"waiting for Neo4j ({attempt}/{attempts}): {exc.__class__.__name__}")
            time.sleep(pause_seconds)
    raise RuntimeError("Neo4j seed failed") from last_error


def main() -> None:
    path = write_sample_catalog(resolve_catalog_path(ROOT))
    print(f"wrote {path}")
    seed_neo4j()


if __name__ == "__main__":
    main()
