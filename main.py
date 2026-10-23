import sys
from pathlib import Path

from src.plotting import save_chart
from src.scheduler import (
    edf_schedulable, gantt, hyperperiod, liu_layland_bound, load_tasks,
    response_time, rms_priorities, rms_schedulable, utilization,
)


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    project = Path(__file__).resolve().parent
    if arguments in (["--help"], ["-h"]):
        print("Запуск: python3 main.py [путь к JSON]")
        print("Без аргументов используется data/tasks.json. Времена задаются в целых мс.")
        return 0
    try:
        if len(arguments) > 1:
            raise ValueError("Укажите не более одного пути к JSON. Справка: python3 main.py --help")
        tasks = load_tasks(arguments[0] if arguments else project / "data/tasks.json")
        ordered = rms_priorities(tasks)
        print("Планирование периодических задач: RMS и EDF")
        print("Модель: один процессор, вытеснение, независимые задачи, блокировок нет.")
        print("Все задачи впервые поступают в 0 мс. Переключение контекста не учитывается.")
        print("Времена указаны в миллисекундах; приоритет 1 является наивысшим.")
        print("При равных периодах выше приоритет у задачи, указанной раньше в файле.\n")
        print(f"{'Задача':<20} {'C':>5} {'T':>5} {'D':>5} {'Приоритет':>10}")
        for priority, task in enumerate(ordered, 1):
            print(f"{task.name:<20} {task.C:>5} {task.T:>5} {task.D:>5} {priority:>10}")
        load = utilization(tasks)
        bound = liu_layland_bound(len(tasks))
        print(f"\nЗагрузка процессора U = {load:.5f} ({load:.2%})")
        print(f"Граница Лю-Лейланда U_LL = {bound:.5f}")
        rms = rms_schedulable(tasks)
        if rms is None:
            print("Тест Лю-Лейланда: не применяется, поскольку есть D != T.")
        elif rms:
            print("Тест Лю-Лейланда: пройден, планируемость RMS гарантирована.")
        else:
            print("Тест Лю-Лейланда: не пройден. Это не доказывает непланируемость RMS.")
        edf = edf_schedulable(tasks)
        if edf is None:
            print("EDF: при D != T требуется другой анализ, условие U <= 1 неприменимо.")
        elif edf:
            print("EDF: U <= 1, набор планируем при D = T.")
        else:
            print("EDF: U > 1, набор непланируем.")
        print("\nПроверка дедлайнов RMS по RTA (B = 0):")
        if any(task.D > task.T for task in tasks):
            print("При D > T нужен анализ нескольких активаций; RTA не выполняется.")
        else:
            print(f"{'Задача':<20} {'C':>5} {'T':>5} {'D':>5} {'R, мс':>12}  {'Уложилась'}")
            all_met = True
            has_estimate = False
            for index, task in enumerate(ordered):
                estimate, stable = response_time(task, ordered[:index])
                has_estimate = has_estimate or not stable
                met = stable and estimate <= task.D
                all_met = all_met and met
                value = str(estimate) if stable else f">= {estimate}*"
                print(f"{task.name:<20} {task.C:>5} {task.T:>5} {task.D:>5} {value:>12}  {'Да' if met else 'Нет'}")
            if has_estimate:
                print("* Оценка превысила дедлайн до стабилизации; это не точное время отклика.")
            print("RTA: все дедлайны соблюдены." if all_met else "RTA: обнаружено нарушение дедлайна.")
        interval = hyperperiod(tasks)
        print(f"\nГиперпериод: {interval} мс")
        segments = gantt(tasks, interval)
        path = save_chart(tasks, segments, interval, project / "docs/rms_gantt.png")
        print(f"Диаграмма RMS сохранена: {path}")
        return 0
    except (OSError, ValueError, ImportError) as error:
        if isinstance(error, ImportError):
            print("Ошибка: не найдена библиотека для построения диаграммы.", file=sys.stderr)
            print("Установите зависимости: python3 -m pip install -r requirements.txt", file=sys.stderr)
        elif isinstance(error, OSError):
            print("Ошибка: не удалось сохранить диаграмму. Проверьте доступ к каталогу docs.", file=sys.stderr)
        else:
            print(f"Ошибка: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
