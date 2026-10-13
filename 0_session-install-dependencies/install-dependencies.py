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

"""Install the runtime dependency into the active Python environment.

The job and the application add src/ to the import path, so this session
does not build the project package. Building it inside a Cloudera session
fails the engine.
"""

import os
import subprocess
import sys
from pathlib import Path


def project_root() -> Path:
    """Find the repository root when CML runs this file inside a session."""

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


def _neo4j_importable() -> bool:
    try:
        import neo4j  # noqa: F401
    except ImportError:
        return False
    return True


def main() -> None:
    if _neo4j_importable():
        print("neo4j is already installed.", flush=True)
        return
    root = project_root()
    requirements = root / "requirements.txt"
    if not requirements.is_file():
        raise SystemExit(f"requirements.txt was not found at {requirements}")
    print(f"Python {sys.version}", flush=True)
    print(f"Installing {requirements}", flush=True)
    base = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "-r",
        str(requirements),
    ]
    attempts = (
        base,
        [*base, "--user"],
        [*base, "--break-system-packages"],
    )
    last_error: subprocess.CalledProcessError | None = None
    for command in attempts:
        print("+", " ".join(command), flush=True)
        try:
            subprocess.check_call(command)
        except subprocess.CalledProcessError as exc:
            last_error = exc
            print(f"pip install failed with status {exc.returncode}", flush=True)
            continue
        print("Installed neo4j.", flush=True)
        return
    raise SystemExit("Could not install neo4j.") from last_error


if __name__ == "__main__":
    main()
