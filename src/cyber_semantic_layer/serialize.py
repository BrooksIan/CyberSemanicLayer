"""JSON snapshot of a semantic catalog."""

import json
import os
from pathlib import Path

from cyber_semantic_layer.catalog import SemanticCatalog
from cyber_semantic_layer.entities import Entity, EntityKind, Relationship
from cyber_semantic_layer.metrics import Metric


def catalog_to_dict(catalog: SemanticCatalog) -> dict:
    return {
        "entities": [
            {
                "id": entity.id,
                "kind": entity.kind.value,
                "name": entity.name,
                "attributes": dict(entity.attributes),
            }
            for entity in catalog.entities()
        ],
        "relationships": [
            {
                "name": relationship.name,
                "from_kind": relationship.from_kind.value,
                "to_kind": relationship.to_kind.value,
                "description": relationship.description,
            }
            for relationship in catalog.relationships()
        ],
        "metrics": [
            {
                "name": metric.name,
                "description": metric.description,
                "entity_kind": metric.entity_kind.value,
                "aggregation": metric.aggregation,
            }
            for metric in catalog.metrics()
        ],
    }


def catalog_from_dict(payload: dict) -> SemanticCatalog:
    catalog = SemanticCatalog()
    for raw in payload.get("entities", []):
        catalog.add_entity(
            Entity(
                id=raw["id"],
                kind=EntityKind(raw["kind"]),
                name=raw["name"],
                attributes=dict(raw.get("attributes", {})),
            )
        )
    for raw in payload.get("relationships", []):
        catalog.add_relationship(
            Relationship(
                name=raw["name"],
                from_kind=EntityKind(raw["from_kind"]),
                to_kind=EntityKind(raw["to_kind"]),
                description=raw["description"],
            )
        )
    for raw in payload.get("metrics", []):
        catalog.add_metric(
            Metric(
                name=raw["name"],
                description=raw["description"],
                entity_kind=EntityKind(raw["entity_kind"]),
                aggregation=raw["aggregation"],
            )
        )
    return catalog


def write_catalog(catalog: SemanticCatalog, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(catalog_to_dict(catalog), indent=2) + "\n", encoding="utf-8")


def read_catalog(path: Path) -> SemanticCatalog:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return catalog_from_dict(payload)


def resolve_catalog_path(root: Path) -> Path:
    """Resolve CATALOG_PATH against the repository root when it is relative."""

    raw = os.environ.get("CATALOG_PATH", "assets/data/catalog.json")
    path = Path(raw)
    if not path.is_absolute():
        path = root / path
    return path
