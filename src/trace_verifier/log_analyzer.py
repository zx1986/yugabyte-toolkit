import re
from typing import Dict, List

from .rule_parser import Stage


def analyze_log(log_path: str, stages: List[Stage]) -> Dict[str, bool]:
    compiled_patterns = {
        stage.id: re.compile(stage.pattern)
        for stage in stages
    }

    results = {stage.id: False for stage in stages}

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            for stage_id, pattern in compiled_patterns.items():
                if not results[stage_id] and pattern.search(line):
                    results[stage_id] = True

    return results
