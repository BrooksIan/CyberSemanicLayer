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

import os
import sys
import time
from pathlib import Path


def project_root() -> Path:
    """Find the repository root when CML runs this file inside a session.

    A session executes the script in a notebook cell, so __file__ is not set.
    """

    for key in ("CDSW_PROJECT_DIR", "ML_PROJECT_DIR"):
        value = os.environ.get(key)
        if value:
            return Path(value)
    start = Path.cwd()
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    file_name = globals().get("__file__")
    if file_name:
        here = Path(file_name).resolve()
        for candidate in here.parents:
            if (candidate / "pyproject.toml").is_file():
                return candidate
    return start


ROOT = project_root()
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
    if not os.environ.get("NEO4J_REQUIRED"):
        attempts = min(attempts, 3)
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
    message = "Neo4j seed failed"
    if os.environ.get("NEO4J_REQUIRED"):
        raise RuntimeError(message) from last_error
    print(
        f"{message}. The catalog snapshot was still written. "
        "In CML there is no Neo4j on localhost. Set NEO4J_REQUIRED=1 to make a missed seed fail the job."
    )


def main() -> None:
    path = write_sample_catalog(resolve_catalog_path(ROOT))
    print(f"wrote {path}")
    seed_neo4j()


if __name__ == "__main__":
    main()
