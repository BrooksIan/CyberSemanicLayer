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
    for key in ("CDSW_PROJECT_DIR", "ML_PROJECT_DIR"):
        value = os.environ.get(key)
        if value:
            return Path(value)
    cwd = Path.cwd()
    if (cwd / "pyproject.toml").is_file():
        return cwd
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return cwd


def main() -> None:
    root = project_root()
    requirements = root / "requirements.txt"
    print(f"Python {sys.version}", flush=True)
    print(f"Installing {requirements}", flush=True)
    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "-r",
        str(requirements),
    ]
    print("+", " ".join(command), flush=True)
    try:
        subprocess.check_call(command)
    except subprocess.CalledProcessError:
        print("pip install failed; retrying with --user", flush=True)
        subprocess.check_call([*command, "--user"])
    print("Installed neo4j.", flush=True)


if __name__ == "__main__":
    main()
