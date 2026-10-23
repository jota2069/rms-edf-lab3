import os
from pathlib import Path

from src.scheduler import rms_priorities


def save_chart(tasks, segments, interval, path):
    project = Path(__file__).resolve().parents[1]
    os.environ.setdefault("MPLCONFIGDIR", str(project / ".mplconfig"))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    ordered = rms_priorities(tasks)
    labels = [task.name for task in ordered] + ["Простой"]
    positions = {task.name: index for index, task in enumerate(ordered)}
    positions[None] = len(ordered)
    colors = plt.get_cmap("tab10")
    figure, axis = plt.subplots(figsize=(11, 4))
    try:
        for start, end, name in segments:
            row = positions[name]
            axis.broken_barh(
                [(start, end - start)], (row - 0.3, 0.6),
                facecolors="lightgray" if name is None else colors(row % 10),
                edgecolors="black", linewidth=0.6,
            )
        axis.set_yticks(range(len(labels)), labels)
        axis.set_ylim(len(labels) - 0.5, -0.5)
        axis.set_xlim(0, interval)
        if interval <= 40:
            axis.set_xticks(range(interval + 1))
        else:
            axis.xaxis.set_major_locator(MaxNLocator(nbins=20, integer=True))
        axis.set_xlabel("Время, мс")
        axis.set_title("Расписание RMS на одном процессоре")
        axis.set_axisbelow(True)
        axis.grid(axis="x", alpha=0.3)
        figure.tight_layout()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(path, dpi=160, metadata={"Software": "matplotlib"})
    finally:
        plt.close(figure)
    return path
