"""Registry of entities, relationships, and metrics."""

from cyber_semantic_layer.entities import Entity, EntityKind, Relationship
from cyber_semantic_layer.metrics import Metric


class SemanticCatalog:
    """In-memory catalog. Replace storage later without changing callers."""

    def __init__(self) -> None:
        self._entities: dict[str, Entity] = {}
        self._relationships: dict[str, Relationship] = {}
        self._metrics: dict[str, Metric] = {}

    def add_entity(self, entity: Entity) -> None:
        if entity.id in self._entities:
            raise ValueError(f"entity already registered: {entity.id}")
        self._entities[entity.id] = entity

    def add_relationship(self, relationship: Relationship) -> None:
        if relationship.name in self._relationships:
            raise ValueError(f"relationship already registered: {relationship.name}")
        self._relationships[relationship.name] = relationship

    def add_metric(self, metric: Metric) -> None:
        if metric.name in self._metrics:
            raise ValueError(f"metric already registered: {metric.name}")
        self._metrics[metric.name] = metric

    def entities(self, kind: EntityKind | None = None) -> list[Entity]:
        values = self._entities.values()
        if kind is None:
            return list(values)
        return [entity for entity in values if entity.kind is kind]

    def relationships(self) -> list[Relationship]:
        return list(self._relationships.values())

    def metrics(self, kind: EntityKind | None = None) -> list[Metric]:
        values = self._metrics.values()
        if kind is None:
            return list(values)
        return [metric for metric in values if metric.entity_kind is kind]
