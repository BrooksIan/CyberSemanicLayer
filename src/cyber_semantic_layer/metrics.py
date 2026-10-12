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
