from typing import Callable

TASKS: list[Callable[[], dict | None]] = []


def register_task(task: Callable[[], dict | None]) -> None:
    if task not in TASKS:
        TASKS.append(task)


def tasks() -> list[Callable[[], dict | None]]:
    return list(TASKS)
