import json
from pathlib import Path

import main as application
from src.plotting import save_chart
from src.scheduler import gantt, load_tasks


ROOT = Path(__file__).resolve().parents[1]


def test_plot(tmp_path):
    tasks = load_tasks(ROOT / "data/tasks.json")
    path = save_chart(tasks, gantt(tasks, 20), 20, tmp_path / "docs/chart.png")
    assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    import matplotlib.pyplot as plt

    assert plt.get_fignums() == []


def test_cli(tmp_path, monkeypatch, capsys):
    captured = []

    def save(tasks, segments, interval, path):
        captured.append((segments, interval, path))
        return path

    monkeypatch.setattr(application, "save_chart", save)
    assert application.main([]) == 0
    output = capsys.readouterr()
    assert output.err == ""
    for text in ["0.75000 (75.00%)", "0.77976", "RTA: все дедлайны соблюдены.",
                 "Гиперпериод: 20 мс", "Тест Лю-Лейланда: пройден", "EDF: U <= 1"]:
        assert text in output.out
    assert captured[0][1:] == (20, ROOT / "docs/rms_gantt.png")
    assert captured[0][0][2:5] == [(4, 5, "Связь"), (5, 7, "Управление"), (7, 9, "Связь")]
    assert application.main(["--help"]) == 0
    assert "Запуск:" in capsys.readouterr().out

    path = tmp_path / "tasks.json"
    for deadline, message in [(1, "RTA: все дедлайны соблюдены."), (6, "RTA не выполняется")]:
        path.write_text(json.dumps([{"name": "А", "C": 1, "T": 5, "D": deadline}]), encoding="utf-8")
        assert application.main([str(path)]) == 0
        output = capsys.readouterr().out
        assert "EDF: при D != T требуется другой анализ" in output
        assert "Тест Лю-Лейланда: не применяется" in output
        assert message in output

    path.write_text(json.dumps([{"name": "А", "C": 2, "T": 3, "D": 3},
                                {"name": "Б", "C": 3, "T": 5, "D": 5}]), encoding="utf-8")
    assert application.main([str(path)]) == 0
    output = capsys.readouterr().out
    for text in [">= 7*", "это не точное время отклика", "RTA: обнаружено нарушение дедлайна",
                 "Это не доказывает непланируемость", "EDF: U > 1"]:
        assert text in output


def test_cli_errors(tmp_path, monkeypatch, capsys):
    for arguments in (["missing.json"], ["a.json", "b.json"]):
        assert application.main(arguments) == 1
        output = capsys.readouterr().err
        assert "Ошибка:" in output and "Traceback" not in output

    path = tmp_path / "bad.json"
    for data, message in [
        ("{", "проверьте синтаксис"),
        ('[{"name":"А","C":1,"T":0,"D":5}]', "T должно быть положительным целым числом"),
        ('[{"name":"А","C":1,"T":100001,"D":100001}]', "Интервал моделирования"),
    ]:
        path.write_text(data, encoding="utf-8")
        assert application.main([str(path)]) == 1
        output = capsys.readouterr().err
        assert message in output and "Traceback" not in output

    for error, message in [(OSError(), "не удалось сохранить диаграмму"),
                           (ImportError(), "Установите зависимости")]:
        def fail(*args):
            raise error

        monkeypatch.setattr(application, "save_chart", fail)
        assert application.main([]) == 1
        output = capsys.readouterr().err
        assert message in output and "Traceback" not in output
