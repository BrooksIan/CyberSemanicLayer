"""Neo4j store for the shadow-admin posture demo.

jdoe is not a Domain Admin. A password-reset permission still reaches
Prod-DB-01 through admin_user. The same graph answers guessed walks and
Ossie-bound paths.
"""

import os
import re
from dataclasses import dataclass, replace

DEMO_TAG = "shadow-admin"
RETIRED_DEMO_TAGS = ("inc-1042", "shadow-admin")
DEFAULT_URI = "bolt://localhost:7687"
DEFAULT_USER = "neo4j"
DEFAULT_PASSWORD = "cyber-semantic-layer"

SEED_STATEMENTS: tuple[str, ...] = (
    "MATCH (n) WHERE n.demo IN $demos DETACH DELETE n",
    """
    CREATE (jdoe:User:Principal {demo: $demo, id: 'user-jdoe', name: 'jdoe'})
    CREATE (admin:User:Principal {demo: $demo, id: 'user-admin', name: 'admin_user'})
    CREATE (aws:User:Principal {demo: $demo, id: 'user-aws', name: 'service_account_aws'})
    CREATE (contractor:User:Principal {demo: $demo, id: 'user-contractor', name: 'contractor'})
    CREATE (breakglass:User:Principal {demo: $demo, id: 'user-break-glass', name: 'break_glass'})
    CREATE (ws:Host:Computer {
      demo: $demo, id: 'host-workstation-01', name: 'Workstation-01',
      environment: 'office', zone: 'office'
    })
    CREATE (jump:Host:Computer {
      demo: $demo, id: 'host-jumpserver-02', name: 'JumpServer-02',
      environment: 'production', zone: 'dmz'
    })
    CREATE (db:Host:Computer {
      demo: $demo, id: 'host-prod-db-01', name: 'Prod-DB-01',
      environment: 'production', zone: 'restricted'
    })
    CREATE (domain_admins:Group {demo: $demo, id: 'group-domain-admins', name: 'Domain Admins'})
    CREATE (aws_role:Group {demo: $demo, id: 'group-aws-admin', name: 'AWS-Admin-Role'})
    CREATE (pci:CriticalAsset {
      demo: $demo, id: 'asset-pci-database', name: 'PCI-Database', classification: 'pci'
    })
    CREATE (cve:Vulnerability:Vuln {
      demo: $demo, id: 'vuln-prod-db', name: 'CVE-2024-3094',
      severity: 'critical', host: 'Prod-DB-01'
    })
    CREATE (jdoe)-[:AUTHENTICATED_TO]->(ws)
    CREATE (jdoe)-[:AUTHENTICATED_TO]->(jump)
    CREATE (jdoe)-[:HAS_PERMISSION {permission: 'ForceChangePassword'}]->(admin)
    CREATE (admin)-[:MEMBER_OF]->(domain_admins)
    CREATE (breakglass)-[:MEMBER_OF]->(domain_admins)
    CREATE (breakglass)-[:AUTHENTICATED_TO]->(db)
    CREATE (domain_admins)-[:HAS_ACCESS_TO]->(db)
    CREATE (aws)-[:MEMBER_OF]->(aws_role)
    CREATE (aws_role)-[:HAS_ACCESS_TO]->(pci)
    CREATE (db)-[:HOSTS]->(pci)
    CREATE (contractor)-[:LOGON]->(ws)
    CREATE (cve)-[:VULNERABILITY_ON_ASSET]->(db)
    """,
)


@dataclass(frozen=True)
class PostureQuestion:
    id: str
    title: str
    prompt: str
    without_cypher: str
    with_cypher: str
    without_names: tuple[str, ...]
    with_names: tuple[str, ...]
    subject: str = ""
    alias_from: str = ""


QUESTIONS: tuple[PostureQuestion, ...] = (
    PostureQuestion(
        id="shadow",
        title="Shadow admin",
        prompt="Which hosts can jdoe reach?",
        without_cypher=(
            "MATCH (u:User {name: 'jdoe', demo: 'shadow-admin'})-[*1..4]->(h:Host) "
            "RETURN DISTINCT h.name AS name ORDER BY name"
        ),
        with_cypher=(
            "MATCH (u:User {name: 'jdoe', demo: 'shadow-admin'}) "
            "CALL (u) { "
            "MATCH (u)-[:HAS_PERMISSION {permission: 'ForceChangePassword'}]->(:User)"
            "-[:MEMBER_OF]->(:Group)-[:HAS_ACCESS_TO]->(h:Host) "
            "RETURN h.name AS name "
            "UNION "
            "MATCH (u)-[:MEMBER_OF]->(:Group)-[:HAS_ACCESS_TO]->(h:Host) "
            "RETURN h.name AS name "
            "} "
            "RETURN DISTINCT name ORDER BY name"
        ),
        without_names=("JumpServer-02", "Prod-DB-01", "Workstation-01"),
        with_names=("Prod-DB-01",),
    ),
    PostureQuestion(
        id="lateral",
        title="Lateral movement",
        prompt="Who is on Workstation-01?",
        without_cypher=(
            "MATCH (u:User {demo: 'shadow-admin'})"
            "-[:LOGON|HAS_SESSION|AUTHENTICATED_TO]->(:Host {name: 'Workstation-01'}) "
            "RETURN u.name AS name ORDER BY name"
        ),
        with_cypher=(
            "MATCH (u:User {demo: 'shadow-admin'})"
            "-[:AUTHENTICATED_TO]->(:Host {name: 'Workstation-01'}) "
            "RETURN u.name AS name ORDER BY name"
        ),
        without_names=("contractor", "jdoe"),
        with_names=("jdoe",),
    ),
    PostureQuestion(
        id="pci",
        title="Critical asset",
        prompt="Who can read PCI-Database?",
        without_cypher=(
            "MATCH (u:User {demo: 'shadow-admin'})-[*1..4]->(h:Host {name: 'PCI-Database'}) "
            "RETURN DISTINCT u.name AS name ORDER BY name"
        ),
        with_cypher=(
            "MATCH (u:User {demo: 'shadow-admin'})-[:MEMBER_OF]->(g:Group) "
            "WHERE (g)-[:HAS_ACCESS_TO]->(:CriticalAsset {name: 'PCI-Database'}) "
            "OR (g)-[:HAS_ACCESS_TO]->(:Host)-[:HOSTS]->(:CriticalAsset {name: 'PCI-Database'}) "
            "RETURN DISTINCT u.name AS name ORDER BY name"
        ),
        without_names=(),
        with_names=("admin_user", "break_glass", "service_account_aws"),
    ),
    PostureQuestion(
        id="members",
        title="Group membership",
        prompt="Who is in the Domain Admins group?",
        without_cypher=(
            "MATCH (u:User {demo: 'shadow-admin'})-[*1..3]-(g:Group {name: 'Domain Admins'}) "
            "RETURN DISTINCT u.name AS name ORDER BY name"
        ),
        with_cypher=(
            "MATCH (u:User {demo: 'shadow-admin'})-[:MEMBER_OF]->(g:Group {name: 'Domain Admins'}) "
            "RETURN DISTINCT u.name AS name ORDER BY name"
        ),
        without_names=("admin_user", "break_glass", "jdoe"),
        with_names=("admin_user", "break_glass"),
    ),
)


_USERS = {
    "jdoe": "jdoe",
    "admin_user": "admin_user",
    "admin user": "admin_user",
    "user_admin": "admin_user",
    "user admin": "admin_user",
    "admin-user": "admin_user",
    "user-admin": "admin_user",
    "service_account_aws": "service_account_aws",
    "service account aws": "service_account_aws",
    "contractor": "contractor",
    "break_glass": "break_glass",
    "break glass": "break_glass",
}
_REACH_SUBJECT = re.compile(r"which hosts can (.+?) reach\b")


@dataclass(frozen=True)
class PreparedQuestion:
    question: PostureQuestion | None
    message: str = ""


def prepare_question(text: str) -> PreparedQuestion:
    """Match a question, then bind a named user on the reach query."""

    question = match_question(text)
    if question is None or question.id != "shadow":
        return PreparedQuestion(question)
    normalized = " ".join(text.casefold().split())
    found = _REACH_SUBJECT.search(normalized)
    if found is None:
        return PreparedQuestion(question)
    raw = found.group(1).strip()
    for article in ("the ", "user "):
        if raw.startswith(article) and raw[len(article):] in _USERS:
            raw = raw[len(article):]
    canonical = _USERS.get(raw)
    if canonical is None:
        known = ", ".join(sorted({name for name in _USERS.values()}))
        return PreparedQuestion(
            None,
            f"The model has no user named {raw}. Users are {known}.",
        )
    if canonical == "jdoe":
        return PreparedQuestion(question)
    bound = replace(
        question,
        prompt=f"Which hosts can {canonical} reach?",
        without_cypher=question.without_cypher.replace("{name: 'jdoe'", f"{{name: '{canonical}'"),
        with_cypher=question.with_cypher.replace("{name: 'jdoe'", f"{{name: '{canonical}'"),
        subject=canonical,
        alias_from="" if raw == canonical else raw,
    )
    return PreparedQuestion(bound)


def match_question(text: str) -> PostureQuestion | None:
    """Map a typed question onto one semantic-model query.

    The application answers only questions the model defines. Unrelated text
    and raw Cypher stay unmatched.
    """

    normalized = " ".join(text.casefold().split())
    if not normalized:
        return None
    for question in QUESTIONS:
        if normalized in {question.prompt.casefold(), question.title.casefold()}:
            return question
    scores = {
        "pci": _hits(normalized, ("pci-database", "pci", "who can read", "critical asset")),
        "lateral": _hits(normalized, ("workstation-01", "workstation", "who is on", "lateral")),
        "members": _hits(normalized, ("who is in", "member of", "members of", "belongs to")),
        "shadow": _hits(
            normalized,
            ("which hosts", "jdoe reach", "jdoe", "shadow", "prod-db", "password"),
        ),
    }
    best_score = max(scores.values())
    if best_score == 0:
        return None
    for question_id in ("members", "pci", "lateral", "shadow"):
        if scores[question_id] == best_score:
            return next(question for question in QUESTIONS if question.id == question_id)
    return None


def _hits(text: str, phrases: tuple[str, ...]) -> int:
    return sum(1 for phrase in phrases if phrase in text)


@dataclass(frozen=True)
class GraphView:
    """Nodes and relationships on the paths a query returned."""

    nodes: tuple[tuple[str, str], ...] = ()
    edges: tuple[tuple[str, str, str], ...] = ()


EMPTY_GRAPH = GraphView()

_PREFERRED_LABELS = ("User", "Host", "Group", "CriticalAsset", "Vulnerability")

PATH_CYPHER: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "shadow": (
        (
            "MATCH path = (u:User {name: 'jdoe', demo: 'shadow-admin'})-[*1..4]->(h:Host) "
            "RETURN path",
        ),
        (
            "MATCH path = (u:User {name: 'jdoe', demo: 'shadow-admin'})"
            "-[:HAS_PERMISSION {permission: 'ForceChangePassword'}]->(:User)"
            "-[:MEMBER_OF]->(:Group)-[:HAS_ACCESS_TO]->(h:Host) "
            "RETURN path",
            "MATCH path = (u:User {name: 'jdoe', demo: 'shadow-admin'})"
            "-[:MEMBER_OF]->(:Group)-[:HAS_ACCESS_TO]->(h:Host) "
            "RETURN path",
        ),
    ),
    "lateral": (
        (
            "MATCH path = (u:User {demo: 'shadow-admin'})"
            "-[:LOGON|HAS_SESSION|AUTHENTICATED_TO]->(:Host {name: 'Workstation-01'}) "
            "RETURN path",
        ),
        (
            "MATCH path = (u:User {demo: 'shadow-admin'})"
            "-[:AUTHENTICATED_TO]->(:Host {name: 'Workstation-01'}) "
            "RETURN path",
        ),
    ),
    "pci": (
        (
            "MATCH path = (u:User {demo: 'shadow-admin'})-[*1..4]->(h:Host {name: 'PCI-Database'}) "
            "RETURN path",
        ),
        (
            "MATCH path = (u:User {demo: 'shadow-admin'})-[:MEMBER_OF]->(:Group)"
            "-[:HAS_ACCESS_TO]->(:CriticalAsset {name: 'PCI-Database'}) "
            "RETURN path",
            "MATCH path = (u:User {demo: 'shadow-admin'})-[:MEMBER_OF]->(:Group)"
            "-[:HAS_ACCESS_TO]->(:Host)-[:HOSTS]->(:CriticalAsset {name: 'PCI-Database'}) "
            "RETURN path",
        ),
    ),
    "members": (
        (
            "MATCH path = (u:User {demo: 'shadow-admin'})-[*1..3]-(g:Group {name: 'Domain Admins'}) "
            "RETURN path",
        ),
        (
            "MATCH path = (u:User {demo: 'shadow-admin'})-[:MEMBER_OF]->(g:Group {name: 'Domain Admins'}) "
            "RETURN path",
        ),
    ),
}


def _primary_label(node) -> str:
    labels = set(node.labels)
    for label in _PREFERRED_LABELS:
        if label in labels:
            return label
    return next(iter(labels), "Node")


def graph_from_paths(paths) -> GraphView:
    nodes: dict[str, str] = {}
    edges: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for path in paths:
        path_nodes = list(path.nodes)
        for node in path_nodes:
            name = node.get("name") or "unnamed"
            nodes.setdefault(name, _primary_label(node))
        for index, relationship in enumerate(path.relationships):
            source = relationship.start_node.get("name") or path_nodes[index].get("name") or "unnamed"
            target = relationship.end_node.get("name") or path_nodes[index + 1].get("name") or "unnamed"
            nodes.setdefault(source, _primary_label(relationship.start_node))
            nodes.setdefault(target, _primary_label(relationship.end_node))
            label = relationship.type
            permission = relationship.get("permission")
            if permission:
                label = f"{label} ({permission})"
            item = (source, label, target)
            if item not in seen:
                seen.add(item)
                edges.append(item)
    ordered = tuple((name, nodes[name]) for name in sorted(nodes))
    return GraphView(nodes=ordered, edges=tuple(edges))


def _collect_graph(session, statements: tuple[str, ...]) -> GraphView:
    paths = []
    for statement in statements:
        paths.extend(record["path"] for record in session.run(statement))
    return graph_from_paths(paths)


@dataclass(frozen=True)
class PostureResult:
    question: PostureQuestion
    without_names: tuple[str, ...]
    with_names: tuple[str, ...]
    without_graph: GraphView = EMPTY_GRAPH
    with_graph: GraphView = EMPTY_GRAPH


def neo4j_config() -> tuple[str, str, str]:
    return (
        os.environ.get("NEO4J_URI", DEFAULT_URI),
        os.environ.get("NEO4J_USER", DEFAULT_USER),
        os.environ.get("NEO4J_PASSWORD", DEFAULT_PASSWORD),
    )


def neo4j_enabled() -> bool:
    return bool(os.environ.get("NEO4J_URI"))


def seed_demo(driver) -> None:
    """Replace the shadow-admin subgraph. Other nodes in the database stay."""

    with driver.session() as session:
        for statement in SEED_STATEMENTS:
            session.run(statement, demo=DEMO_TAG, demos=list(RETIRED_DEMO_TAGS))


def _bind_name(statements: tuple[str, ...], subject: str) -> tuple[str, ...]:
    if not subject or subject == "jdoe":
        return statements
    return tuple(statement.replace("{name: 'jdoe'", "{name: '" + subject + "'") for statement in statements)


def run_question(driver, question: PostureQuestion) -> PostureResult:
    without_paths, with_paths = PATH_CYPHER[question.id]
    without_paths = _bind_name(without_paths, question.subject)
    with_paths = _bind_name(with_paths, question.subject)
    with driver.session() as session:
        without_names = tuple(record["name"] for record in session.run(question.without_cypher))
        with_names = tuple(record["name"] for record in session.run(question.with_cypher))
        without_graph = _collect_graph(session, without_paths)
        with_graph = _collect_graph(session, with_paths)
    return PostureResult(
        question=question,
        without_names=without_names,
        with_names=with_names,
        without_graph=without_graph,
        with_graph=with_graph,
    )


def run_posture(driver) -> list[PostureResult]:
    results: list[PostureResult] = []
    with driver.session() as session:
        for question in QUESTIONS:
            without_names = tuple(
                record["name"] for record in session.run(question.without_cypher)
            )
            with_names = tuple(record["name"] for record in session.run(question.with_cypher))
            results.append(
                PostureResult(
                    question=question,
                    without_names=without_names,
                    with_names=with_names,
                )
            )
    return results


def open_driver():
    from neo4j import GraphDatabase

    uri, user, password = neo4j_config()
    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    return driver
