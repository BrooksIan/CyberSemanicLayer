from cyber_semantic_layer.neo4j_graph import QUESTIONS, SEED_STATEMENTS, match_question, prepare_question


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
