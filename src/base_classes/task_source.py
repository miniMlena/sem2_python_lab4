from collections.abc import Iterable
from typing import Protocol, runtime_checkable
from src.base_classes.task import Task

# runtime_checkable делает так, что isinstance, issubclass используют протокол для провекри
@runtime_checkable
class TaskSource(Protocol):
    '''
    Протокол, описывающий поведение источника задач
    '''
    name: str

    def get_tasks(self) -> Iterable[Task]:
        ...