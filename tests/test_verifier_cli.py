from unittest.mock import patch
import pytest
from src.trace_verifier.cli import main
from src.trace_verifier.rule_parser import ValidationConfig, Stage


def _make_config(stages):
    return ValidationConfig(name="Test", description="Desc", stages=stages)


@patch("src.trace_verifier.cli.sys.argv", ["cli.py", "--rules", "dummy.yaml", "--log-file", "dummy.log"])
@patch("src.trace_verifier.cli.parse_rules")
@patch("src.trace_verifier.cli.analyze_log")
def test_cli_all_pass(mock_analyze, mock_parse, capsys):
    stage = Stage(id="1", name="Step1", pattern="abc", required=True)
    mock_parse.return_value = _make_config([stage])
    mock_analyze.return_value = {"1": True}

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "[✔] Step1" in out
    assert "VERIFICATION PASSED" in out


@patch("src.trace_verifier.cli.sys.argv", ["cli.py", "--rules", "dummy.yaml", "--log-file", "dummy.log"])
@patch("src.trace_verifier.cli.parse_rules")
@patch("src.trace_verifier.cli.analyze_log")
def test_cli_required_missing_exits_1(mock_analyze, mock_parse, capsys):
    stage = Stage(id="1", name="Step1", pattern="abc", required=True)
    mock_parse.return_value = _make_config([stage])
    mock_analyze.return_value = {"1": False}

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "[✖] Step1 (Missing)" in out
    assert "VERIFICATION FAILED" in out


@patch("src.trace_verifier.cli.sys.argv", ["cli.py", "--rules", "dummy.yaml", "--log-file", "dummy.log"])
@patch("src.trace_verifier.cli.parse_rules")
@patch("src.trace_verifier.cli.analyze_log")
def test_cli_optional_missing_still_passes(mock_analyze, mock_parse, capsys):
    stage = Stage(id="1", name="OptStep", pattern="abc", required=False)
    mock_parse.return_value = _make_config([stage])
    mock_analyze.return_value = {"1": False}

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "[-] OptStep (Missing, Optional)" in out
    assert "VERIFICATION PASSED" in out
