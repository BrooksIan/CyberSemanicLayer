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

from cyber_semantic_layer.seed import build_sample_catalog

_APP_PATH = Path(__file__).resolve().parents[1] / "2_app-browse-catalog" / "app.py"
_SPEC = importlib.util.spec_from_file_location("browse_catalog_app", _APP_PATH)
assert _SPEC is not None and _SPEC.loader is not None
APP = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(APP)


def test_posture_table_renders_both_answers() -> None:
    from cyber_semantic_layer.neo4j_graph import PostureResult, QUESTIONS

    row = PostureResult(
        question=QUESTIONS[0],
        without_names=("JumpServer-02", "Prod-DB-01", "Workstation-01"),
        with_names=("Prod-DB-01",),
    )
    page = APP.render_catalog(
        build_sample_catalog(),
        "notice",
        APP.render_posture([row], "Queried Neo4j at bolt://localhost:7687."),
    )
    assert "Without Ossie" in page
    assert "With Ossie" in page
    assert "Prod-DB-01" in page
    assert "ForceChangePassword" in page
    assert "How Ossie helped" in page
    assert "access_grants" in page


def test_query_form_rejects_text_outside_the_model() -> None:
    page = APP.render_catalog(
        build_sample_catalog(),
        "notice",
        query_html=APP.render_query_form(
            "drop the database",
            APP.render_answer("drop the database", None, None, "No semantic-model query matches that question."),
        ),
    )
    assert 'name="question"' in page
    assert "No answer" in page
    assert "No semantic-model query matches" in page
    assert "Ask" in page


def test_answer_explains_how_ossie_helped() -> None:
    from cyber_semantic_layer.neo4j_graph import PostureResult, QUESTIONS

    question = QUESTIONS[1]
    result = PostureResult(question=question, without_names=("contractor", "jdoe"), with_names=("jdoe",))
    page = APP.render_answer(question.prompt, question, result, "Queried Neo4j.")
    assert "How Ossie helped" in page
    assert "AUTHENTICATED_TO" in page
    assert "LOGON stays a different event type" in page


def test_graph_view_draws_the_returned_path() -> None:
    from cyber_semantic_layer.neo4j_graph import GraphView, PostureResult, QUESTIONS

    question = QUESTIONS[0]
    graph = GraphView(
        nodes=(
            ("Domain Admins", "Group"),
            ("Prod-DB-01", "Host"),
            ("admin_user", "User"),
            ("jdoe", "User"),
        ),
        edges=(
            ("jdoe", "HAS_PERMISSION (ForceChangePassword)", "admin_user"),
            ("admin_user", "MEMBER_OF", "Domain Admins"),
        ),
    )
    result = PostureResult(
        question=question,
        without_names=("Workstation-01",),
        with_names=("Prod-DB-01",),
        without_graph=GraphView(),
        with_graph=graph,
    )
    page = APP.render_answer(question.prompt, question, result, "Queried Neo4j.")
    assert "<svg" in page
    assert "Prod-DB-01" in page
    assert 'fill="#dcfce7"' in page
    assert 'fill="#dbeafe"' in page
    assert 'fill="#ede9fe"' in page
    assert "HAS_PERMISSION (ForceChangePassword)" in page
    assert "No path returned." in page


def test_render_hides_the_sample_catalog() -> None:
    page = APP.render_catalog(build_sample_catalog(), "sample notice")
    assert "web-01" not in page
    assert "alert_on_asset" not in page
    assert "open_alert_count" not in page
    assert "<h2>Entities</h2>" not in page


def test_missing_snapshot_uses_sample(tmp_path: Path) -> None:
    catalog, notice = APP.load_catalog(tmp_path / "missing.json")
    assert "built-in sample" in notice
    assert any(entity.name == "web-01" for entity in catalog.entities())


def test_snapshot_is_loaded(tmp_path: Path) -> None:
    from cyber_semantic_layer.serialize import write_catalog

    path = tmp_path / "catalog.json"
    write_catalog(build_sample_catalog(), path)
    catalog, notice = APP.load_catalog(path)
    assert str(path) in notice
    assert any(entity.id == "incident-1042" for entity in catalog.entities())
