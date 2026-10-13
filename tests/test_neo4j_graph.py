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

from cyber_semantic_layer.neo4j_graph import (
    QUESTIONS,
    SEED_STATEMENTS,
    demo_result,
    match_question,
    prepare_question,
)


def test_each_question_has_two_cypher_forms() -> None:
    ids = [question.id for question in QUESTIONS]
    assert ids == ["shadow", "lateral", "pci", "members"]
    for question in QUESTIONS:
        assert question.without_names != question.with_names


def test_seed_builds_both_label_sets() -> None:
    seed = "\n".join(SEED_STATEMENTS)
    for token in (
        "AUTHENTICATED_TO",
        "HAS_PERMISSION",
        "MEMBER_OF",
        "HAS_ACCESS_TO",
        "HOSTS",
        "LOGON",
        "PCI-Database",
        "JumpServer-02",
        "service_account_aws",
        "ForceChangePassword",
    ):
        assert token in seed
    assert "MATCH (n) WHERE n.demo IN $demos DETACH DELETE n" in seed


def test_typed_questions_map_onto_the_model() -> None:
    assert match_question("can jdoe access prod-db").id == "shadow"
    assert match_question("Which hosts can jdoe reach?").id == "shadow"
    assert match_question("who is on workstation-01").id == "lateral"
    assert match_question("Who can read the PCI database?").id == "pci"
    assert match_question("Who is in Domain Admins group?").id == "members"
    bound = prepare_question("Which hosts can user_admin reach?")
    assert bound.question is not None
    assert bound.question.subject == "admin_user"
    assert bound.question.alias_from == "user_admin"
    assert "admin_user" in bound.question.without_cypher
    assert "jdoe" not in bound.question.without_cypher
    assert prepare_question("Which hosts can jdoe reach?").question.subject == ""
    missing = prepare_question("Which hosts can nobody reach?")
    assert missing.question is None
    assert "nobody" in missing.message
    assert match_question("MATCH (n) DETACH DELETE n") is None
    assert match_question("what is the weather") is None


def test_demo_graph_answers_each_question_without_neo4j() -> None:
    by_id = {question.id: question for question in QUESTIONS}
    lateral = demo_result(by_id["lateral"])
    assert lateral.without_names == ("contractor", "jdoe")
    assert lateral.with_names == ("jdoe",)
    assert ("contractor", "LOGON", "Workstation-01") in lateral.without_graph.edges
    assert ("jdoe", "AUTHENTICATED_TO", "Workstation-01") in lateral.with_graph.edges
    assert all(label == "AUTHENTICATED_TO" for _source, label, _target in lateral.with_graph.edges)

    for question in QUESTIONS:
        result = demo_result(question)
        assert result.without_names == question.without_names
        assert result.with_names == question.with_names

    rebound = prepare_question("Which hosts can contractor reach?")
    assert rebound.question is not None
    contractor = demo_result(rebound.question)
    assert contractor.without_names == ("Workstation-01",)
    assert contractor.with_names == ()
