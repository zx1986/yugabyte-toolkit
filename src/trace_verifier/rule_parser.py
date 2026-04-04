from dataclasses import dataclass
from typing import List

import yaml


@dataclass
class Stage:
    id: str
    name: str
    pattern: str
    required: bool


@dataclass
class ValidationConfig:
    name: str
    description: str
    stages: List[Stage]


def parse_rules(yaml_path: str) -> ValidationConfig:
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    stages = [
        Stage(
            id=s["id"],
            name=s["name"],
            pattern=s["pattern"],
            required=s.get("required", True),
        )
        for s in data.get("stages", [])
    ]
    return ValidationConfig(
        name=data.get("name", ""),
        description=data.get("description", ""),
        stages=stages,
    )
