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

import pytest

from cyber_semantic_layer import Entity, EntityKind, Metric, Relationship, SemanticCatalog


def test_catalog_registers_and_filters() -> None:
    catalog = SemanticCatalog()
    catalog.add_entity(Entity(id="asset-1", kind=EntityKind.ASSET, name="web-01"))
    catalog.add_entity(Entity(id="alert-1", kind=EntityKind.ALERT, name="suspicious-login"))
    catalog.add_relationship(
        Relationship(
            name="alert_on_asset",
            from_kind=EntityKind.ALERT,
            to_kind=EntityKind.ASSET,
            description="Alert observed against an asset.",
        )
    )
    catalog.add_metric(
        Metric(
            name="open_alert_count",
            description="Count of open alerts.",
            entity_kind=EntityKind.ALERT,
            aggregation="count",
        )
    )

    assert [entity.id for entity in catalog.entities(EntityKind.ASSET)] == ["asset-1"]
    assert catalog.relationships()[0].name == "alert_on_asset"
    assert catalog.metrics(EntityKind.ALERT)[0].name == "open_alert_count"


def test_duplicate_entity_is_rejected() -> None:
    catalog = SemanticCatalog()
    entity = Entity(id="asset-1", kind=EntityKind.ASSET, name="web-01")
    catalog.add_entity(entity)

    with pytest.raises(ValueError, match="entity already registered"):
        catalog.add_entity(entity)
