import json
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path


MAX_ITERATIONS = 10000


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


def rms_priorities(tasks):
    validate_tasks(tasks)
    # При равных периодах сохраняем порядок задач из файла.
    return sorted(tasks, key=lambda task: task.T)


def utilization(tasks):
    validate_tasks(tasks)
    return float(sum((Fraction(task.C, task.T) for task in tasks), Fraction(0)))


def liu_layland_bound(n):
    if type(n) is not int or n <= 0:
        raise ValueError("Число задач должно быть положительным целым числом.")
    return n * (2 ** (1 / n) - 1)


def rms_schedulable(tasks):
    """Достаточный тест Лю-Лейланда; None означает неприменимость теста."""
    validate_tasks(tasks)
    if any(task.D != task.T for task in tasks):
        return None
    return utilization(tasks) <= liu_layland_bound(len(tasks))


def edf_schedulable(tasks):
    validate_tasks(tasks)
    if any(task.D != task.T for task in tasks):
        return None
    return sum((Fraction(task.C, task.T) for task in tasks), Fraction(0)) <= 1


def response_time(task, higher):
    """Возвращает (оценка, стабилизировалась). B=0, независимые задачи, D<=T."""
    higher = list(higher)
    validate_tasks([task] + higher)
    if task.D > task.T or any(other.D > other.T for other in higher):
        raise ValueError("Для RTA при D > T нужен анализ нескольких активаций.")
    if any(other.T > task.T for other in higher):
        raise ValueError("Список higher не соответствует приоритетам RMS.")
    estimate = task.C
    if estimate > task.D:
        return estimate, False
    for _ in range(MAX_ITERATIONS):
        # Целочисленное округление вверх не теряет точность на больших числах.
        next_estimate = task.C + sum(
            ((estimate + other.T - 1) // other.T) * other.C for other in higher
        )
        if next_estimate == estimate:
            return estimate, True
        if next_estimate > task.D:
            return next_estimate, False
        estimate = next_estimate
    raise ValueError("RTA: достигнут предел итераций, результат не определён.")
