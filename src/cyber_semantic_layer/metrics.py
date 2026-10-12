"""Metrics defined on top of domain entities."""

from dataclasses import dataclass

from cyber_semantic_layer.entities import EntityKind


@dataclass(frozen=True)
class Metric:
    """A named measure scoped to one entity kind."""

    name: str
    description: str
    entity_kind: EntityKind
    aggregation: str
