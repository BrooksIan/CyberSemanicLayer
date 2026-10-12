"""Domain entities and the relationships between them."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class EntityKind(str, Enum):
    """Kinds of objects the semantic layer can describe."""

    ASSET = "asset"
    IDENTITY = "identity"
    ALERT = "alert"
    VULNERABILITY = "vulnerability"
    INCIDENT = "incident"


@dataclass(frozen=True)
class Entity:
    """One named object in the security domain."""

    id: str
    kind: EntityKind
    name: str
    attributes: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Relationship:
    """A directed link from one entity kind to another."""

    name: str
    from_kind: EntityKind
    to_kind: EntityKind
    description: str
