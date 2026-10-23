import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Task:
    name: str
    C: int
    T: int
    D: int

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Имя задачи должно быть непустой строкой.")
        for field in ("C", "T", "D"):
            value = getattr(self, field)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{self.name}: {field} должно быть положительным целым числом.")


def validate_tasks(tasks):
    if not tasks or any(not isinstance(task, Task) for task in tasks):
        raise ValueError("Нужен непустой список задач Task.")
    names = [task.name for task in tasks]
    if len(set(names)) != len(names):
        raise ValueError("Имена задач должны быть уникальными.")


def load_tasks(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError) as error:
        raise ValueError("Не удалось прочитать JSON: проверьте синтаксис и кодировку UTF-8.") from error
    except OSError as error:
        raise ValueError(f"Не удалось открыть файл задач: {path}") from error
    if not isinstance(data, list) or not data:
        raise ValueError("JSON должен содержать непустой массив задач.")
    tasks = []
    for item in data:
        if not isinstance(item, dict) or set(item) != {"name", "C", "T", "D"}:
            raise ValueError("Каждая задача должна содержать только поля name, C, T, D.")
        tasks.append(Task(**item))
    validate_tasks(tasks)
    return tasks
