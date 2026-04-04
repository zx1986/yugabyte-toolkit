import pytest
from src.trace_verifier.rule_parser import Stage
from src.trace_verifier.log_analyzer import analyze_log


def test_analyze_log_matches_patterns(tmp_path):
    log_content = (
        "[pod-0] Random startup logs\n"
        "[pod-1] statement: INSERT INTO test_table (id) VALUES (1)\n"
        "[pod-0] Appending to Raft Log\n"
        "[pod-2] Ignoring some other thing\n"
    )
    log_file = tmp_path / "trace.log"
    log_file.write_text(log_content)

    stages = [
        Stage(id="1", name="YSQL", pattern="statement: INSERT INTO test_table", required=True),
        Stage(id="2", name="Raft", pattern="Appending to Raft Log", required=True),
        Stage(id="3", name="Missing", pattern="Not found in log", required=True),
    ]

    results = analyze_log(str(log_file), stages)
    assert results["1"] is True
    assert results["2"] is True
    assert results["3"] is False


def test_analyze_log_regex_pattern(tmp_path):
    log_content = "Sending UpdateConsensus to follower peer 1234\n"
    log_file = tmp_path / "trace.log"
    log_file.write_text(log_content)

    stages = [
        Stage(id="r", name="Replicate", pattern=r"Sending UpdateConsensus.*peer \d+", required=True),
    ]

    results = analyze_log(str(log_file), stages)
    assert results["r"] is True


def test_analyze_log_empty_file(tmp_path):
    log_file = tmp_path / "empty.log"
    log_file.write_text("")

    stages = [
        Stage(id="1", name="Stage", pattern="anything", required=True),
    ]

    results = analyze_log(str(log_file), stages)
    assert results["1"] is False
