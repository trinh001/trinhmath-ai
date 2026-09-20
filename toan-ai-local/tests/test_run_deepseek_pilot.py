from run_deepseek_pilot import (
    EXPECTED_TASK_COUNT,
    ensure_fast_only,
    load_synthetic_tasks,
    run_pilot,
)


def test_launcher_loads_exactly_five_synthetic_fast_tasks():
    tasks = load_synthetic_tasks()
    assert len(tasks) == EXPECTED_TASK_COUNT == 5
    ensure_fast_only(tasks)


def test_launcher_defaults_to_offline_dry_run_without_key(capsys):
    exit_code = run_pilot(live=False, environment={})
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "MODE: DRY_RUN" in output
    assert "TASKS RUN: 5 / 5" in output
    assert "API CALLS: 0" in output


def test_live_launcher_fails_closed_without_local_environment(capsys):
    exit_code = run_pilot(live=True, environment={})
    output = capsys.readouterr().out
    assert exit_code == 2
    assert "PREFLIGHT: BLOCKED" in output
    assert "API CALLS: 0" in output
    assert "DEEPSEEK_API_KEY" not in output
