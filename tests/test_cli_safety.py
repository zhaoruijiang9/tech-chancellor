from pathlib import Path

from pti.cli import validate_output_root


def test_money_path_is_never_an_output_target(tmp_path):
    assert validate_output_root(tmp_path).allowed
    assert not validate_output_root(Path("D:/money")).allowed


def test_dry_run_has_no_execution_surface():
    from pti.cli import ALLOWED_PHASE_1_ACTIONS

    assert ALLOWED_PHASE_1_ACTIONS == {"discover", "score", "route", "report"}
