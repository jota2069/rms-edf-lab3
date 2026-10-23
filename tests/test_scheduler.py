from pathlib import Path

import pytest

import src.scheduler as scheduler
from src.scheduler import (
    Task, edf_schedulable, gantt, hyperperiod, liu_layland_bound,
    load_tasks, response_time, rms_priorities, rms_schedulable, utilization,
)


@pytest.fixture
def tasks():
    return load_tasks(Path(__file__).resolve().parents[1] / "data/tasks.json")


def test_utilization(tasks):
    assert utilization(tasks) == pytest.approx(0.75)
    assert utilization([Task("А", 2, 3, 3), Task("Б", 3, 5, 5)]) == pytest.approx(19 / 15)


def test_bound():
    for n, expected in [(1, 1), (2, 0.8284271247461903), (3, 0.7797631496846196)]:
        assert liu_layland_bound(n) == pytest.approx(expected)
    for n in (0, -1, True, 2.5, "3"):
        with pytest.raises(ValueError):
            liu_layland_bound(n)


def test_rms_test(tasks):
    assert rms_schedulable(tasks) is True
    assert rms_schedulable([Task("А", 9, 10, 10), Task("Б", 1, 10, 10)]) is False
    assert rms_schedulable([Task("А", 5, 5, 5)]) is True
    assert rms_schedulable([Task("А", 1, 5, 1)]) is None


def test_edf(tasks):
    assert edf_schedulable(tasks) is True
    for cost, expected in [(9, True), (10, True), (11, False)]:
        assert edf_schedulable([Task("А", cost, 10, 10)]) is expected
    assert edf_schedulable([Task("А", 1, 10, 10), Task("Б", 9, 10, 10)]) is True
    assert edf_schedulable([Task("А", 10**18 + 1, 10**18, 10**18)]) is False


def test_edf_other_deadlines():
    for deadline in (3, 6):
        assert edf_schedulable([Task("А", 1, 5, deadline)]) is None


def test_response_times(tasks):
    ordered = rms_priorities(tasks)
    assert [response_time(task, ordered[:i]) for i, task in enumerate(ordered)] == [
        (2, True), (4, True), (9, True)]


def test_response_deadline():
    high = Task("А", 2, 5, 5)
    assert response_time(Task("Б", 3, 10, 5), [high]) == (5, True)
    assert response_time(Task("Б", 4, 10, 5), [high]) == (6, False)
    assert response_time(Task("Б", 7, 10, 5), []) == (7, False)


def test_response_ceiling_boundary():
    assert response_time(Task("Б", 3, 12, 12), [Task("А", 2, 5, 5)]) == (5, True)
    assert response_time(Task("Б", 4, 12, 12), [Task("А", 2, 5, 5)]) == (8, True)


def test_rta_guard(monkeypatch):
    monkeypatch.setattr(scheduler, "MAX_ITERATIONS", 2)
    with pytest.raises(ValueError, match="предел итераций"):
        response_time(Task("Б", 3, 20, 20), [Task("А", 2, 3, 3)])


def test_rta_constraints():
    with pytest.raises(ValueError, match="нескольких активаций"):
        response_time(Task("А", 1, 5, 6), [])
    with pytest.raises(ValueError, match="приоритетам"):
        response_time(Task("А", 1, 5, 5), [Task("Б", 1, 10, 10)])


def test_ll_failure_rta_success():
    tasks = [Task("А", 2, 4, 4), Task("Б", 3, 8, 8)]
    assert utilization(tasks) == 0.875
    assert rms_schedulable(tasks) is False
    assert response_time(tasks[0], []) == (2, True)
    assert response_time(tasks[1], tasks[:1]) == (7, True)


def test_hyperperiod(tasks):
    assert hyperperiod(tasks) == 20
    assert hyperperiod([Task("А", 1, 6, 6), Task("Б", 1, 8, 8)]) == 24
    assert hyperperiod([Task("А", 1, 7, 7)]) == 7


def test_load_json(tasks):
    assert tasks == [Task("Управление", 2, 5, 5), Task("Датчики", 2, 10, 10), Task("Связь", 3, 20, 20)]


def test_priorities(tasks):
    unsorted = [tasks[2], tasks[0], tasks[1]]
    assert rms_priorities(unsorted) == tasks
    assert unsorted == [tasks[2], tasks[0], tasks[1]]
    first, second = Task("Б", 1, 5, 5), Task("А", 1, 5, 5)
    assert rms_priorities([first, second]) == [first, second]
    assert gantt([first, second], 2) == [(0, 1, "Б"), (1, 2, "А")]


def test_variant_schedule(tasks):
    assert gantt(list(reversed(tasks)), 20) == [
        (0, 2, "Управление"), (2, 4, "Датчики"), (4, 5, "Связь"),
        (5, 7, "Управление"), (7, 9, "Связь"), (9, 10, None),
        (10, 12, "Управление"), (12, 14, "Датчики"), (14, 15, None),
        (15, 17, "Управление"), (17, 20, None),
    ]


def test_preemption():
    tasks = [Task("Связь", 4, 10, 10), Task("Управление", 1, 3, 3)]
    assert gantt(tasks, 7) == [
        (0, 1, "Управление"), (1, 3, "Связь"), (3, 4, "Управление"),
        (4, 6, "Связь"), (6, 7, "Управление")]


def test_idle_and_boundary():
    tasks = [Task("А", 1, 3, 3)]
    assert gantt(tasks, 1) == [(0, 1, "А")]
    assert gantt(tasks, 3) == [(0, 1, "А"), (1, 3, None)]
    assert gantt(tasks, 4) == [(0, 1, "А"), (1, 3, None), (3, 4, "А")]


def test_queued_jobs():
    # В t=7 новое поступление не должно стереть остаток предыдущего.
    assert gantt([Task("А", 2, 5, 5), Task("Б", 4, 7, 7)], 14) == [
        (0, 2, "А"), (2, 5, "Б"), (5, 7, "А"), (7, 10, "Б"),
        (10, 12, "А"), (12, 14, "Б")]
    assert gantt([Task("А", 4, 3, 3)], 10) == [(0, 10, "А")]


def test_invalid_interval(tasks, monkeypatch):
    for interval in (0, -1, 2.5, True, 100001):
        with pytest.raises(ValueError, match="Интервал"):
            gantt(tasks, interval)
    monkeypatch.setattr(scheduler, "MAX_INTERVAL", 4)
    assert gantt([Task("А", 1, 3, 3)], 4) == [(0, 1, "А"), (1, 3, None), (3, 4, "А")]
    with pytest.raises(ValueError):
        gantt(tasks, 5)


def test_invalid_task():
    for field in ("C", "T", "D"):
        for value in (0, -1, 1.5, True, "2", None):
            values = {"name": "А", "C": 1, "T": 5, "D": 5}
            values[field] = value
            with pytest.raises(ValueError, match=field):
                Task(**values)
    for name in ("", "  ", 3, None):
        with pytest.raises(ValueError, match="Имя"):
            Task(name, 1, 5, 5)


def test_invalid_json(tmp_path):
    path = tmp_path / "tasks.json"
    cases = ["{", "[]", "{}", "null", '[{"name":"А","C":1,"T":5}]',
             '[{"name":"А","C":1,"T":5,"D":5,"extra":1}]', '[1]',
             '[{"name":"А","C":true,"T":5,"D":5}]',
             '[{"name":"А","C":1,"T":5,"D":5},{"name":"А","C":1,"T":5,"D":5}]']
    for data in cases:
        path.write_text(data, encoding="utf-8")
        with pytest.raises(ValueError):
            load_tasks(path)
    path.write_bytes(b"\xff")
    with pytest.raises(ValueError, match="кодировку"):
        load_tasks(path)
    with pytest.raises(ValueError, match="открыть файл"):
        load_tasks(tmp_path / "missing.json")


def test_invalid_collections():
    for function in (utilization, rms_priorities, rms_schedulable, edf_schedulable, hyperperiod):
        for tasks in ([], [1]):
            with pytest.raises(ValueError):
                function(tasks)
