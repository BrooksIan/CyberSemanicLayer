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

import json
import re
from pathlib import Path

from cyber_semantic_layer.entities import EntityKind
from cyber_semantic_layer.seed import build_sample_catalog
from cyber_semantic_layer.serialize import catalog_from_dict, catalog_to_dict, write_catalog, read_catalog

ROOT = Path(__file__).resolve().parents[1]


def test_sample_catalog_covers_each_kind() -> None:
    catalog = build_sample_catalog()
    kinds = {entity.kind for entity in catalog.entities()}
    assert kinds == set(EntityKind)
    assert {metric.name for metric in catalog.metrics()} == {
        "open_alert_count",
        "critical_vulnerability_count",
        "open_incident_count",
    }


def test_catalog_json_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "catalog.json"
    write_catalog(build_sample_catalog(), path)
    restored = read_catalog(path)
    assert catalog_to_dict(restored) == catalog_to_dict(build_sample_catalog())
    assert catalog_from_dict(json.loads(path.read_text(encoding="utf-8"))).entities()


def test_amp_scripts_exist() -> None:
    metadata = (ROOT / ".project-metadata.yaml").read_text(encoding="utf-8")
    scripts = re.findall(r"(?m)^[ ]*script:\s+(\S+)\s*$", metadata)
    assert scripts
    for script in scripts:
        path = ROOT / script
        assert path.is_file(), script
        source = path.read_text(encoding="utf-8")
        assert "!pip" not in source
