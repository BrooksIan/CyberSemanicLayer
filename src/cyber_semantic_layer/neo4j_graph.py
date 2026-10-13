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


def _merge_graphs(base: GraphView, extra: GraphView) -> GraphView:
    nodes = dict(base.nodes)
    for name, kind in extra.nodes:
        nodes.setdefault(name, kind)
    edges = list(base.edges)
    seen = set(edges)
    for edge in extra.edges:
        if edge not in seen:
            seen.add(edge)
            edges.append(edge)
    ordered = tuple((name, nodes[name]) for name in sorted(nodes))
    return GraphView(nodes=ordered, edges=tuple(edges))


def _attach_vulnerabilities(session, graph: GraphView) -> GraphView:
    hosts = [name for name, kind in graph.nodes if kind == "Host"]
    if not hosts:
        return graph
    paths = [
        record["path"]
        for record in session.run(
            "MATCH path = (v:Vulnerability {demo: $demo})-[:VULNERABILITY_ON_ASSET]->(h:Host) "
            "WHERE h.name IN $hosts RETURN path",
            demo=DEMO_TAG,
            hosts=hosts,
        )
    ]
    if not paths:
        return graph
    return _merge_graphs(graph, graph_from_paths(paths))


def _collect_graph(session, statements: tuple[str, ...]) -> GraphView:
    paths = []
    for statement in statements:
        paths.extend(record["path"] for record in session.run(statement))
    return _attach_vulnerabilities(session, graph_from_paths(paths))


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


_Edge = tuple[str, str, str]
_KINDS = {
    "jdoe": "User",
    "admin_user": "User",
    "service_account_aws": "User",
    "contractor": "User",
    "break_glass": "User",
    "Workstation-01": "Host",
    "JumpServer-02": "Host",
    "Prod-DB-01": "Host",
    "Domain Admins": "Group",
    "AWS-Admin-Role": "Group",
    "PCI-Database": "CriticalAsset",
    "CVE-2024-3094": "Vulnerability",
}
_EDGES: tuple[_Edge, ...] = (
    ("jdoe", "AUTHENTICATED_TO", "Workstation-01"),
    ("jdoe", "AUTHENTICATED_TO", "JumpServer-02"),
    ("jdoe", "HAS_PERMISSION (ForceChangePassword)", "admin_user"),
    ("admin_user", "MEMBER_OF", "Domain Admins"),
    ("break_glass", "MEMBER_OF", "Domain Admins"),
    ("break_glass", "AUTHENTICATED_TO", "Prod-DB-01"),
    ("Domain Admins", "HAS_ACCESS_TO", "Prod-DB-01"),
    ("service_account_aws", "MEMBER_OF", "AWS-Admin-Role"),
    ("AWS-Admin-Role", "HAS_ACCESS_TO", "PCI-Database"),
    ("Prod-DB-01", "HOSTS", "PCI-Database"),
    ("contractor", "LOGON", "Workstation-01"),
    ("CVE-2024-3094", "VULNERABILITY_ON_ASSET", "Prod-DB-01"),
)


def _steps(node: str, undirected: bool) -> list[tuple[str, _Edge]]:
    steps: list[tuple[str, _Edge]] = []
    for source, label, target in _EDGES:
        if source == node:
            steps.append((target, (source, label, target)))
        elif undirected and target == node:
            steps.append((source, (source, label, target)))
    return steps


def _walk(start: str, hops: int, undirected: bool, arrived) -> list[list[_Edge]]:
    found: list[list[_Edge]] = []
    queue: list[tuple[str, list[_Edge], set[str]]] = [(start, [], {start})]
    while queue:
        node, path, seen = queue.pop(0)
        if path and arrived(node):
            found.append(path)
        if len(path) >= hops:
            continue
        for nxt, edge in _steps(node, undirected):
            if nxt in seen:
                continue
            queue.append((nxt, [*path, edge], seen | {nxt}))
    return found


def _view(paths: list[list[_Edge]]) -> GraphView:
    nodes: dict[str, str] = {}
    edges: list[_Edge] = []
    seen: set[_Edge] = set()
    for path in paths:
        for source, label, target in path:
            nodes.setdefault(source, _KINDS[source])
            nodes.setdefault(target, _KINDS[target])
            edge = (source, label, target)
            if edge not in seen:
                seen.add(edge)
                edges.append(edge)
    return GraphView(
        nodes=tuple((name, nodes[name]) for name in sorted(nodes)),
        edges=tuple(edges),
    )


def _sorted_names(names: set[str]) -> tuple[str, ...]:
    return tuple(sorted(names))


def _shadow_with(user: str) -> list[list[_Edge]]:
    paths: list[list[_Edge]] = []
    for first in _steps(user, False):
        _nxt, edge = first
        if not edge[1].startswith("HAS_PERMISSION") or _KINDS.get(edge[2]) != "User":
            continue
        for _group, member in _steps(edge[2], False):
            if member[1] != "MEMBER_OF":
                continue
            for host, access in _steps(member[2], False):
                if access[1] == "HAS_ACCESS_TO" and _KINDS.get(host) == "Host":
                    paths.append([edge, member, access])
    for group, member in _steps(user, False):
        if member[1] != "MEMBER_OF":
            continue
        for host, access in _steps(group, False):
            if access[1] == "HAS_ACCESS_TO" and _KINDS.get(host) == "Host":
                paths.append([member, access])
    return paths


def _lateral(types: set[str]) -> list[list[_Edge]]:
    return [
        [(source, label, target)]
        for source, label, target in _EDGES
        if target == "Workstation-01" and label in types and _KINDS.get(source) == "User"
    ]


def _pci_with() -> list[list[_Edge]]:
    paths: list[list[_Edge]] = []
    for user, kind in _KINDS.items():
        if kind != "User":
            continue
        for group, member in _steps(user, False):
            if member[1] != "MEMBER_OF":
                continue
            for asset, access in _steps(group, False):
                if access[1] != "HAS_ACCESS_TO":
                    continue
                if asset == "PCI-Database":
                    paths.append([member, access])
                elif _KINDS.get(asset) == "Host":
                    for hosted, hosts in _steps(asset, False):
                        if hosts[1] == "HOSTS" and hosted == "PCI-Database":
                            paths.append([member, access, hosts])
    return paths


def _members_without() -> list[tuple[str, list[_Edge]]]:
    found: list[tuple[str, list[_Edge]]] = []
    for user, kind in _KINDS.items():
        if kind != "User":
            continue
        for path in _walk(user, 3, True, lambda node: node == "Domain Admins"):
            found.append((user, path))
    return found


def demo_result(question: PostureQuestion) -> PostureResult:
    """Answer a question from the seeded demo graph when Neo4j is not configured."""

    subject = question.subject or "jdoe"
    if question.id == "shadow":
        without_paths = _walk(subject, 4, False, lambda node: _KINDS.get(node) == "Host")
        with_paths = _shadow_with(subject)
        without_names = _sorted_names({path[-1][2] for path in without_paths})
        with_names = _sorted_names({path[-1][2] for path in with_paths})
    elif question.id == "lateral":
        without_paths = _lateral({"LOGON", "HAS_SESSION", "AUTHENTICATED_TO"})
        with_paths = _lateral({"AUTHENTICATED_TO"})
        without_names = _sorted_names({path[0][0] for path in without_paths})
        with_names = _sorted_names({path[0][0] for path in with_paths})
    elif question.id == "pci":
        without_paths = []
        for user, kind in _KINDS.items():
            if kind == "User":
                without_paths.extend(
                    path
                    for path in _walk(user, 4, False, lambda node: _KINDS.get(node) == "Host")
                    if path[-1][2] == "PCI-Database"
                )
        with_paths = _pci_with()
        without_names = _sorted_names({path[0][0] for path in without_paths})
        with_names = _sorted_names({path[0][0] for path in with_paths})
    else:
        without_found = _members_without()
        without_paths = [path for _user, path in without_found]
        with_paths = [
            [(user, "MEMBER_OF", "Domain Admins")]
            for user, kind in _KINDS.items()
            if kind == "User"
            and (user, "MEMBER_OF", "Domain Admins") in _EDGES
        ]
        without_names = _sorted_names({user for user, _path in without_found})
        with_names = _sorted_names({path[0][0] for path in with_paths})
    return PostureResult(
        question=question,
        without_names=without_names,
        with_names=with_names,
        without_graph=_view(without_paths),
        with_graph=_view(with_paths),
    )


def open_driver():
    from neo4j import GraphDatabase

    uri, user, password = neo4j_config()
    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    return driver
