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

"""Browse the semantic catalog over HTTP."""

import html
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cyber_semantic_layer.catalog import SemanticCatalog
from cyber_semantic_layer.seed import build_sample_catalog
from cyber_semantic_layer.serialize import read_catalog, resolve_catalog_path


def load_catalog(path: Path) -> tuple[SemanticCatalog, str]:
    if path.is_file():
        return read_catalog(path), f"Loaded catalog snapshot from {path}."
    catalog = build_sample_catalog()
    return catalog, "Catalog snapshot was not found. Showing the built-in sample."


def render_query_form(submitted: str, answer_html: str) -> str:
    from cyber_semantic_layer.neo4j_graph import QUESTIONS

    examples = " ".join(
        '<a href="/?question={href}">{label}</a>'.format(
            href=urllib.parse.quote(question.prompt),
            label=html.escape(question.prompt),
        )
        for question in QUESTIONS
    )
    return f"""<section class="panel">
<h2>Ask a question</h2>
<form method="get" action="/#answer">
  <label for="question">Question for the semantic layer</label>
  <textarea id="question" name="question" rows="3" required>{html.escape(submitted)}</textarea>
  <button type="submit">Ask</button>
</form>
<p class="examples">Examples: {examples}</p>
{answer_html}
</section>
"""


def ossie_help(question) -> str:
    question_id = question if isinstance(question, str) else question.id
    subject = "" if isinstance(question, str) else question.subject
    alias = "" if isinstance(question, str) else question.alias_from
    if question_id == "shadow" and subject and subject != "jdoe":
        named = f"{alias} is {subject} in the model. " if alias else ""
        return (
            named
            + f"Reach for {subject} is bound to ForceChangePassword when that permission exists, "
            "and to MEMBER_OF then HAS_ACCESS_TO when the user is in a group that can open a host. "
            "AUTHENTICATED_TO and LOGON are sessions, so they leave this answer."
        )
    if question_id == "shadow":
        return (
            "Reach is bound to permissions, then memberships, then access_grants. "
            "The permission value is ForceChangePassword. MEMBER_OF and HAS_ACCESS_TO "
            "are the next relationships. jdoe reaches Prod-DB-01 by resetting admin_user's "
            "password. Workstation-01 and JumpServer-02 are sessions, so they leave this answer."
        )
    if question_id == "members":
        return (
            "In the group is bound to memberships, and that relationship is MEMBER_OF. "
            "A password-reset permission and a logon to Prod-DB-01 are other relationships, "
            "so they leave this answer. admin_user and break_glass remain."
        )
    if question_id == "lateral":
        return (
            "On is bound to the sessions dataset, and the session relationship is "
            "AUTHENTICATED_TO. LOGON stays a different event type. contractor drops out. "
            "jdoe stays, because that user has an authenticated session on the workstation."
        )
    return (
        "Read is bound to critical_assets, a different dataset from hosts. "
        "HAS_ACCESS_TO reaches the asset directly, and HOSTS reaches it through Prod-DB-01. "
        "A walk that only looks at hosts returns no names. Group membership returns "
        "admin_user, break_glass, and service_account_aws."
    )


def answer_sentences(question, result) -> tuple[str, str]:
    if result is None:
        return ("Neo4j did not return names.", "Neo4j did not return names.")
    without_names = ", ".join(result.without_names) or "no names"
    with_names = ", ".join(result.with_names) or "no names"
    if question.id == "shadow":
        who = question.subject or "jdoe"
        if who == "jdoe":
            return (
                f"Without Ossie, jdoe reaches {without_names}.",
                f"With Ossie, the password-reset path reaches {with_names}.",
            )
        return (
            f"Without Ossie, {who} reaches {without_names}.",
            f"With Ossie, bound reach for {who} includes {with_names}.",
        )
    if question.id == "members":
        return (
            f"Without Ossie, users connected to Domain Admins include {without_names}.",
            f"With Ossie, MEMBER_OF includes {with_names}.",
        )
    if question.id == "lateral":
        return (
            f"Without Ossie, Workstation-01 includes {without_names}.",
            f"With Ossie, an authenticated session includes {with_names}.",
        )
    return (
        f"Without Ossie, a host walk returns {without_names}.",
        f"With Ossie, group access to PCI-Database includes {with_names}.",
    )


_NODE_COLORS = {
    "User": ("#dbeafe", "#1d4ed8"),
    "Group": ("#ede9fe", "#6d28d9"),
    "Host": ("#dcfce7", "#15803d"),
    "CriticalAsset": ("#ffedd5", "#c2410c"),
    "Vulnerability": ("#fee2e2", "#b91c1c"),
}
_NODE_COLOR_FALLBACK = ("#f4f4f5", "#52525b")


def node_colors(kind: str) -> tuple[str, str]:
    return _NODE_COLORS.get(kind, _NODE_COLOR_FALLBACK)


def render_legend(kinds: list[str]) -> str:
    chips = []
    for kind in kinds:
        fill, stroke = node_colors(kind)
        chips.append(
            f'<span class="swatch" style="background:{fill};border-color:{stroke}">'
            f"{html.escape(kind)}</span>"
        )
    if not chips:
        return ""
    return '<p class="legend">' + "".join(chips) + "</p>"


def _relationship_lines(label: str) -> tuple[str, ...]:
    if " (" in label and label.endswith(")"):
        name, detail = label.split(" (", 1)
        return (name, detail[:-1])
    return (label,)


def _label_width(text: str) -> int:
    return int(len(text) * 8.2) + 18


def render_graph(graph, marker_id: str) -> str:
    from cyber_semantic_layer.neo4j_graph import GraphView

    if not isinstance(graph, GraphView) or not graph.nodes:
        return "<p>No path returned.</p>"
    names = [name for name, _kind in graph.nodes]
    depth = {name: 0 for name in names}
    for _name in names:
        for source, _label, target in graph.edges:
            if source in depth and target in depth and _label != "VULNERABILITY_ON_ASSET":
                depth[target] = max(depth[target], depth[source] + 1)
    for source, label, target in graph.edges:
        if label == "VULNERABILITY_ON_ASSET" and target in depth:
            depth[source] = depth[target]
    columns: dict[int, list[str]] = {}
    for name in names:
        columns.setdefault(depth[name], []).append(name)
    for column in columns.values():
        column.sort()
    label_lines = {
        (source, label, target): _relationship_lines(label)
        for source, label, target in graph.edges
    }
    chip_widths = [
        max(_label_width(line) for line in lines) for lines in label_lines.values()
    ]
    node_w, node_h, gap_y = 156, 40, 48
    gap_x = max([96, *chip_widths]) + 20
    pad_x, pad_y = 24, 28
    positions: dict[str, tuple[int, int]] = {}
    max_depth = max(columns)
    max_rows = max(len(column) for column in columns.values())
    for column_index, column_names in columns.items():
        for row_index, name in enumerate(column_names):
            x = pad_x + column_index * (node_w + gap_x)
            y = pad_y + row_index * (node_h + gap_y)
            positions[name] = (x, y)
    width = pad_x * 2 + (max_depth + 1) * node_w + max_depth * gap_x
    vuln_label = max(
        (
            max(_label_width(line) for line in lines)
            for (source, label, target), lines in label_lines.items()
            if label == "VULNERABILITY_ON_ASSET"
        ),
        default=0,
    )
    if vuln_label:
        width += vuln_label + 28
    height = pad_y * 2 + max_rows * node_h + max(0, max_rows - 1) * gap_y
    kinds = dict(graph.nodes)
    edge_markup = []
    label_markup = []
    placed: list[tuple[float, float, float, float]] = []
    for source, label, target in graph.edges:
        if source not in positions or target not in positions:
            continue
        x1, y1 = positions[source]
        x2, y2 = positions[target]
        if abs(x1 - x2) < 1:
            start_x = x1 + node_w / 2
            end_x = x2 + node_w / 2
            if y1 <= y2:
                start_y = y1 + node_h
                end_y = y2
            else:
                start_y = y1
                end_y = y2 + node_h
            edge_markup.append(
                f'<line x1="{start_x}" y1="{start_y}" x2="{end_x}" y2="{end_y - 8 if y1 <= y2 else end_y + 8}" '
                f'marker-end="url(#{marker_id})" stroke="#666" />'
            )
        else:
            start_x, start_y = x1 + node_w, y1 + node_h / 2
            end_x, end_y = x2, y2 + node_h / 2
            edge_markup.append(
                f'<line x1="{start_x}" y1="{start_y}" x2="{end_x - 8}" y2="{end_y}" '
                f'marker-end="url(#{marker_id})" stroke="#666" />'
            )
        lines = label_lines[(source, label, target)]
        chip_w = max(_label_width(line) for line in lines)
        chip_h = 16 * len(lines) + 6
        if abs(x1 - x2) < 1:
            center_x = start_x + 12 + chip_w / 2
            center_y = (start_y + end_y) / 2
        elif end_x > start_x:
            center_x = start_x + gap_x / 2
            span = end_x - start_x
            along = min(max((center_x - start_x) / span, 0), 1)
            center_y = start_y + along * (end_y - start_y)
        else:
            center_x = (start_x + end_x) / 2
            center_y = min(start_y, end_y) - chip_h
        left = center_x - chip_w / 2
        top = center_y - chip_h - 4
        margin = 10

        def blocked(candidate: float) -> bool:
            return any(
                left < other_right + margin
                and left + chip_w > other_left - margin
                and candidate < other_bottom + margin
                and candidate + chip_h > other_top - margin
                for other_left, other_top, other_right, other_bottom in placed
            )

        if blocked(top):
            up = top
            down = top
            for _nudge in range(8):
                up -= chip_h + margin
                down += chip_h + margin
                if up >= 8 and not blocked(up):
                    top = up
                    break
                if not blocked(down):
                    top = down
                    break
            else:
                top = down
        placed.append((left, top, left + chip_w, top + chip_h))
        text_rows = []
        for index, line in enumerate(lines):
            text_y = top + 15 + index * 16
            text_rows.append(
                f'<text x="{center_x}" y="{text_y}" text-anchor="middle" font-size="12" '
                f'font-weight="600" fill="#120046">{html.escape(line)}</text>'
            )
        label_markup.append(
            f'<rect x="{left}" y="{top}" width="{chip_w}" height="{chip_h}" rx="4" '
            f'fill="#ffffff" stroke="#e4e0ee" />'
            + "".join(text_rows)
        )
    node_markup = []
    for name, (x, y) in positions.items():
        fill, stroke = node_colors(kinds[name])
        node_markup.append(
            f'<rect x="{x}" y="{y}" width="{node_w}" height="{node_h}" rx="4" '
            f'fill="{fill}" stroke="{stroke}" />'
            f'<text x="{x + node_w / 2}" y="{y + 17}" text-anchor="middle" font-size="12">'
            f"{html.escape(name)}</text>"
            f'<text x="{x + node_w / 2}" y="{y + 32}" text-anchor="middle" font-size="10" fill="{stroke}">'
            f"{html.escape(kinds[name])}</text>"
        )
    label = "; ".join(f"{source} {rel} {target}" for source, rel, target in graph.edges)
    shift = 0
    if placed:
        min_top = min(box[1] for box in placed)
        if min_top < 8:
            shift = 8 - min_top
        max_bottom = max(box[3] for box in placed) + shift
        if max_bottom > height - 8:
            height = int(max_bottom + 8)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="{html.escape(label)}">'
        f'<defs><marker id="{marker_id}" markerWidth="8" markerHeight="8" refX="8" refY="3" orient="auto">'
        f'<path d="M0,0 L8,3 L0,6 Z" fill="#666" /></marker></defs>'
        f'<g transform="translate(0 {shift})">'
        + "".join(edge_markup)
        + "".join(node_markup)
        + "".join(label_markup)
        + "</g></svg>"
    )


def render_answer(submitted: str, question, result, status: str) -> str:
    if question is None:
        detail = status or (
            f"No semantic-model query matches {submitted}. "
            "Ask about jdoe's reach, Workstation-01, Domain Admins, or PCI-Database."
        )
        return (
            '<section id="answer"><h2>No answer</h2>'
            f"<p>{html.escape(detail)}</p></section>"
        )
    if result is None:
        without_names = "not run"
        with_names = "not run"
        without_sentence, with_sentence = (status, status)
    else:
        without_names = ", ".join(result.without_names) or "none"
        with_names = ", ".join(result.with_names) or "none"
        without_sentence, with_sentence = answer_sentences(question, result)
    if result is None:
        without_graph = "<p>No path returned.</p>"
        with_graph = "<p>No path returned.</p>"
        legend = ""
    else:
        without_graph = render_graph(result.without_graph, "arrow-without")
        with_graph = render_graph(result.with_graph, "arrow-with")
        seen = []
        for graph in (result.without_graph, result.with_graph):
            for _name, kind in getattr(graph, "nodes", ()):
                if kind not in seen:
                    seen.append(kind)
        order = list(_NODE_COLORS)
        seen.sort(key=lambda kind: order.index(kind) if kind in order else len(order))
        legend = render_legend(seen)
    return """<section id="answer" class="answer"><h2>Answer</h2>
<p><strong>{without_sentence}</strong></p>
<p><strong>{with_sentence}</strong></p>
<h3>How Ossie helped</h3>
<p>{ossie_help}</p>
<h3>Graph</h3>
{legend}
<div class="graphs">
  <div><p>Without Ossie</p>{without_graph}</div>
  <div><p>With Ossie</p>{with_graph}</div>
</div>
<p>{status} Matched {title}: {prompt}</p>
<table class="compare">
  <thead><tr><th></th><th>Without Ossie</th><th>With Ossie</th></tr></thead>
  <tbody>
    <tr>
      <td>Cypher</td>
      <td><code>{without_cypher}</code></td>
      <td><code>{with_cypher}</code></td>
    </tr>
    <tr>
      <td>Neo4j names</td>
      <td>{without_names}</td>
      <td>{with_names}</td>
    </tr>
  </tbody>
</table>
</section>
""".format(
        submitted=html.escape(submitted),
        status=html.escape(status),
        title=html.escape(question.title),
        prompt=html.escape(question.prompt),
        without_sentence=html.escape(without_sentence),
        with_sentence=html.escape(with_sentence),
        ossie_help=html.escape(ossie_help(question)),
        legend=legend,
        without_graph=without_graph,
        with_graph=with_graph,
        without_cypher=html.escape(question.without_cypher),
        with_cypher=html.escape(question.with_cypher),
        without_names=html.escape(without_names),
        with_names=html.escape(with_names),
    )


def answer_question(text: str):
    from cyber_semantic_layer.neo4j_graph import neo4j_config, open_driver, prepare_question, run_question

    prepared = prepare_question(text)
    question = prepared.question
    if question is None:
        return None, None, prepared.message or "No semantic-model query matches that question."
    uri, _user, _password = neo4j_config()
    if not os.environ.get("NEO4J_URI"):
        return question, None, "NEO4J_URI is unset, so the Cypher was not run."
    try:
        driver = open_driver()
    except Exception as exc:
        return question, None, f"Neo4j at {uri} is not reachable ({exc.__class__.__name__})."
    try:
        return question, run_question(driver, question), f"Queried Neo4j at {uri}."
    finally:
        driver.close()


def render_posture(rows, status: str) -> str:
    if not rows:
        return (
            '<section class="panel"><h2>Posture on Neo4j</h2>'
            f"<p class=\"status\">{html.escape(status)}</p></section>"
        )
    body_rows = "\n".join(
        "<tr><td rowspan=\"2\">{title}</td>"
        "<td rowspan=\"2\">{prompt}<br><em>How Ossie helped:</em> {help}</td>"
        "<td><code>{without_cypher}</code></td>"
        "<td><code>{with_cypher}</code></td></tr>"
        "<tr><td>{without_names}</td><td>{with_names}</td></tr>".format(
            title=html.escape(row.question.title),
            prompt=html.escape(row.question.prompt),
            help=html.escape(ossie_help(row.question)),
            without_cypher=html.escape(row.question.without_cypher),
            without_names=html.escape(", ".join(row.without_names) or "none"),
            with_cypher=html.escape(row.question.with_cypher),
            with_names=html.escape(", ".join(row.with_names) or "none"),
        )
        for row in rows
    )
    return f"""<section class="panel">
<h2>Posture on Neo4j</h2>
<p class="status">{html.escape(status)}</p>
<table class="posture">
  <thead><tr><th>Question</th><th>Ask</th><th>Without Ossie</th><th>With Ossie</th></tr></thead>
  <tbody>
    {body_rows}
  </tbody>
</table>
</section>
"""


def load_posture() -> tuple[list | None, str]:
    from cyber_semantic_layer.neo4j_graph import neo4j_config, open_driver, run_posture

    uri, _user, _password = neo4j_config()
    if not os.environ.get("NEO4J_URI"):
        return None, "NEO4J_URI is unset. Start Neo4j with deploy/docker-compose.yml, then set NEO4J_URI=bolt://localhost:7687."
    try:
        driver = open_driver()
    except Exception as exc:
        return None, f"Neo4j at {uri} is not reachable ({exc.__class__.__name__})."
    try:
        return run_posture(driver), f"Queried Neo4j at {uri}."
    finally:
        driver.close()


def render_catalog(catalog: SemanticCatalog, notice: str, posture_html: str = "", query_html: str = "") -> str:
    del catalog, notice
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Cyber Semantic Layer</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --indigo: #120046;
      --orange: #ff550d;
      --nova: #5555f9;
      --link: #413cc3;
      --paper: #f4f2f8;
      --line: #e4e0ee;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--indigo);
      font-family: "Plus Jakarta Sans", Helvetica, Arial, sans-serif;
      line-height: 1.5;
    }}
    header {{
      background: var(--indigo);
      color: #fff;
      padding: 1.75rem 1.5rem 1.5rem;
    }}
    .brand {{
      margin: 0 0 0.75rem;
      color: var(--orange);
      font-weight: 700;
      letter-spacing: 0.14em;
      font-size: 0.95rem;
    }}
    header h1 {{
      margin: 0;
      font-size: 2.4rem;
      font-weight: 600;
      letter-spacing: -0.03em;
      line-height: 1.1;
    }}
    header h1 span {{ color: var(--orange); }}
    .rule {{
      width: 3rem;
      height: 4px;
      margin: 1rem 0;
      background: var(--orange);
    }}
    header .lede {{
      margin: 0;
      max-width: 40rem;
      color: #f4f2f8;
    }}
    main {{
      max-width: 72rem;
      margin: 0 auto;
      padding: 1.5rem 1.25rem 3rem;
    }}
    .panel {{
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 1.25rem 1.35rem 1.5rem;
      margin: 0 0 1.25rem;
    }}
    h2, h3 {{
      margin: 0 0 0.75rem;
      color: var(--indigo);
      font-weight: 600;
      letter-spacing: -0.02em;
    }}
    h2 {{ font-size: 1.45rem; }}
    h3 {{ margin-top: 1.25rem; font-size: 1.05rem; }}
    label {{ font-weight: 600; }}
    textarea {{
      display: block;
      width: 100%;
      margin: 0.45rem 0 0.75rem;
      padding: 0.75rem 0.85rem;
      border: 1px solid var(--line);
      border-radius: 8px;
      color: var(--indigo);
      font: inherit;
      resize: vertical;
    }}
    textarea:focus {{
      outline: 2px solid var(--nova);
      border-color: transparent;
    }}
    button {{
      background: var(--orange);
      color: #fff;
      border: 0;
      border-radius: 6px;
      padding: 0.65rem 1.25rem;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }}
    button:hover {{ background: #e04808; }}
    a {{ color: var(--link); font-weight: 600; }}
    .examples {{ color: #4b4568; }}
    .examples a {{ margin-right: 0.75rem; }}
    .status {{ color: #4b4568; }}
    .answer {{
      margin-top: 1.25rem;
      padding-top: 0.25rem;
      border-top: 1px solid var(--line);
    }}
    table {{
      width: 100%;
      table-layout: fixed;
      border-collapse: collapse;
      margin: 0.5rem 0 0;
    }}
    .compare th:first-child,
    .compare td:first-child {{
      width: 6.5rem;
    }}
    .posture th:nth-child(1) {{ width: 16%; }}
    .posture th:nth-child(2) {{ width: 28%; }}
    .posture tbody tr:nth-child(odd) td:nth-child(n+3) {{
      border-bottom: 0;
      padding-bottom: 0.35rem;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 0.7rem 0.75rem;
      text-align: left;
      vertical-align: top;
      overflow-wrap: break-word;
    }}
    th {{
      background: var(--indigo);
      color: #fff;
      font-weight: 600;
    }}
    tr:last-child td {{ border-bottom: 0; }}
    code {{
      display: block;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      background: var(--indigo);
      color: #fff;
      border-radius: 8px;
      padding: 0.65rem 0.75rem;
      font-size: 0.78rem;
      line-height: 1.45;
    }}
    .graphs {{
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }}
    .graphs > div {{
      width: 100%;
      background: var(--paper);
      border-radius: 10px;
      padding: 0.75rem;
      overflow-x: auto;
    }}
    .graphs p {{
      margin: 0 0 0.5rem;
      font-size: 0.75rem;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}
    .graphs > div:last-child > p {{ color: var(--orange); }}
    .graphs svg {{
      background: #fff;
      border-radius: 8px;
      max-width: 100%;
      height: auto;
    }}
    .legend {{ display: flex; gap: 0.5rem; flex-wrap: wrap; }}
    .swatch {{
      border: 1px solid;
      border-radius: 999px;
      padding: 0.15rem 0.65rem;
      font-size: 0.8rem;
      font-weight: 600;
    }}
    @media (max-width: 720px) {{
      header h1 {{ font-size: 1.8rem; }}
      .panel {{ padding: 1rem; }}
      .posture th:nth-child(1) {{ width: 22%; }}
      .posture th:nth-child(2) {{ width: 28%; }}
    }}
  </style>
</head>
<body>
  <header>
    <p class="brand">CLOUDERA</p>
    <h1>Cyber <span>Semantic Layer</span></h1>
    <div class="rule"></div>
    <p class="lede">Compare reach with and without the semantic model.</p>
  </header>
  <main>
    {query_html}
    {posture_html}
  </main>
</body>
</html>
"""


def app_port() -> int:
    return int(os.environ.get("PORT") or os.environ.get("CDSW_APP_PORT") or "8080")


def question_from_path(path: str) -> str:
    parsed = urllib.parse.urlparse(path)
    values = urllib.parse.parse_qs(parsed.query)
    return values.get("question", [""])[0].strip()


def question_from_body(raw: str) -> str:
    values = urllib.parse.parse_qs(raw)
    return values.get("question", [""])[0].strip()


def page_bytes(catalog: SemanticCatalog, notice: str, submitted: str) -> bytes:
    answer_html = ""
    if submitted:
        question, result, status = answer_question(submitted)
        answer_html = render_answer(submitted, question, result, status)
    rows, posture_status = load_posture()
    query_html = render_query_form(submitted, answer_html)
    return render_catalog(catalog, notice, render_posture(rows, posture_status), query_html).encode("utf-8")


def make_handler(catalog: SemanticCatalog, notice: str) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _send(self, submitted: str) -> None:
            body = page_bytes(catalog, notice, submitted)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if urllib.parse.urlparse(self.path).path not in ("/", "/index.html"):
                self.send_error(404)
                return
            self._send(question_from_path(self.path))

        def do_POST(self) -> None:
            if urllib.parse.urlparse(self.path).path not in ("/", "/index.html"):
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length > 4000:
                self.send_error(413)
                return
            raw = self.rfile.read(length).decode("utf-8", errors="replace")
            self._send(question_from_body(raw))

        def log_message(self, fmt: str, *args) -> None:
            print(fmt % args)

    return Handler


def serve(host: str = "127.0.0.1", port: int | None = None) -> None:
    catalog_path = resolve_catalog_path(ROOT)
    catalog, notice = load_catalog(catalog_path)
    server = ThreadingHTTPServer((host, app_port() if port is None else port), make_handler(catalog, notice))
    print(f"serving {catalog_path} on http://{host}:{server.server_port}")
    server.serve_forever()


def main() -> None:
    serve()


if __name__ == "__main__":
    main()
