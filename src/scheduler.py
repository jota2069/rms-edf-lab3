from dataclasses import dataclass


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
