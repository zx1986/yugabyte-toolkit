import pytest
from src.trace_verifier.rule_parser import parse_rules


def test_parse_rules_valid_yaml(tmp_path):
    yaml_content = """
name: "Test"
description: "Test description"
stages:
  - id: "stage1"
    name: "First Stage"
    pattern: "hello.*world"
    required: true
"""
    rule_file = tmp_path / "rules.yaml"
    rule_file.write_text(yaml_content)

    config = parse_rules(str(rule_file))
    assert config.name == "Test"
    assert len(config.stages) == 1
    assert config.stages[0].id == "stage1"
    assert config.stages[0].pattern == "hello.*world"


def test_parse_rules_default_required_is_true(tmp_path):
    yaml_content = """
name: "Test"
description: "Desc"
stages:
  - id: "s1"
    name: "Stage"
    pattern: "abc"
"""
    rule_file = tmp_path / "rules.yaml"
    rule_file.write_text(yaml_content)

    config = parse_rules(str(rule_file))
    assert config.stages[0].required is True


def test_parse_rules_optional_stage(tmp_path):
    yaml_content = """
name: "Test"
description: "Desc"
stages:
  - id: "s1"
    name: "Stage"
    pattern: "abc"
    required: false
"""
    rule_file = tmp_path / "rules.yaml"
    rule_file.write_text(yaml_content)

    config = parse_rules(str(rule_file))
    assert config.stages[0].required is False
