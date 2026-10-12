"""Illustrative catalog used by the blueprint job and application."""

from cyber_semantic_layer.catalog import SemanticCatalog
from cyber_semantic_layer.entities import Entity, EntityKind, Relationship
from cyber_semantic_layer.metrics import Metric


def build_sample_catalog() -> SemanticCatalog:
    """Return a small security catalog so the prototype runs before real telemetry is connected."""

    catalog = SemanticCatalog()
    catalog.add_entity(
        Entity(
            id="asset-web-01",
            kind=EntityKind.ASSET,
            name="web-01",
            attributes={"environment": "production", "zone": "dmz"},
        )
    )
    catalog.add_entity(
        Entity(
            id="identity-svc-analyst",
            kind=EntityKind.IDENTITY,
            name="svc-analyst",
            attributes={"type": "service-account"},
        )
    )
    catalog.add_entity(
        Entity(
            id="alert-suspicious-login",
            kind=EntityKind.ALERT,
            name="suspicious-login",
            attributes={"severity": "high", "status": "open"},
        )
    )
    catalog.add_entity(
        Entity(
            id="vuln-cve-2024-12345",
            kind=EntityKind.VULNERABILITY,
            name="CVE-2024-12345",
            attributes={"severity": "critical"},
        )
    )
    catalog.add_entity(
        Entity(
            id="incident-1042",
            kind=EntityKind.INCIDENT,
            name="INC-1042",
            attributes={"status": "investigating"},
        )
    )
    catalog.add_relationship(
        Relationship(
            name="alert_on_asset",
            from_kind=EntityKind.ALERT,
            to_kind=EntityKind.ASSET,
            description="Alert observed against an asset.",
        )
    )
    catalog.add_relationship(
        Relationship(
            name="alert_for_identity",
            from_kind=EntityKind.ALERT,
            to_kind=EntityKind.IDENTITY,
            description="Alert attributed to an identity.",
        )
    )
    catalog.add_relationship(
        Relationship(
            name="vulnerability_on_asset",
            from_kind=EntityKind.VULNERABILITY,
            to_kind=EntityKind.ASSET,
            description="Vulnerability found on an asset.",
        )
    )
    catalog.add_relationship(
        Relationship(
            name="incident_groups_alert",
            from_kind=EntityKind.INCIDENT,
            to_kind=EntityKind.ALERT,
            description="Incident groups one or more alerts.",
        )
    )
    catalog.add_metric(
        Metric(
            name="open_alert_count",
            description="Count of alerts whose status is open.",
            entity_kind=EntityKind.ALERT,
            aggregation="count",
        )
    )
    catalog.add_metric(
        Metric(
            name="critical_vulnerability_count",
            description="Count of vulnerabilities whose severity is critical.",
            entity_kind=EntityKind.VULNERABILITY,
            aggregation="count",
        )
    )
    catalog.add_metric(
        Metric(
            name="open_incident_count",
            description="Count of incidents that are not closed.",
            entity_kind=EntityKind.INCIDENT,
            aggregation="count",
        )
    )
    return catalog
