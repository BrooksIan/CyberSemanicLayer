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

import importlib.util
from pathlib import Path

import pytest

_JOB_PATH = Path(__file__).resolve().parents[1] / "1_job-build-catalog" / "job.py"
_SPEC = importlib.util.spec_from_file_location("build_catalog_job", _JOB_PATH)
assert _SPEC is not None and _SPEC.loader is not None
JOB = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(JOB)


def test_project_root_without_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    (project / "pyproject.toml").write_text("", encoding="utf-8")
    monkeypatch.chdir(project)
    monkeypatch.delenv("CDSW_PROJECT_DIR", raising=False)
    monkeypatch.delenv("ML_PROJECT_DIR", raising=False)
    saved = JOB.__dict__.pop("__file__", None)
    try:
        assert JOB.project_root() == project
    finally:
        if saved is not None:
            JOB.__dict__["__file__"] = saved


def test_unreachable_neo4j_does_not_fail_the_amp_job(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NEO4J_REQUIRED", raising=False)
    monkeypatch.setattr(JOB, "neo4j_enabled", lambda: True)
    monkeypatch.setattr(JOB, "open_driver", _refuse)
    JOB.seed_neo4j(attempts=1, pause_seconds=0)


def test_unreachable_neo4j_fails_when_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEO4J_REQUIRED", "1")
    monkeypatch.setattr(JOB, "neo4j_enabled", lambda: True)
    monkeypatch.setattr(JOB, "open_driver", _refuse)
    with pytest.raises(RuntimeError, match="Neo4j seed failed"):
        JOB.seed_neo4j(attempts=1, pause_seconds=0)


def _refuse():
    raise ConnectionError("refused")
