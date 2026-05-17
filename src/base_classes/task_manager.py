from collections.abc import Sequence, Iterable
from src.base_classes.task import Task
from src.base_classes.task_source import TaskSource

class TaskManager:
    def __init__(self, sources: Sequence[TaskSource] = None) -> None:
        '''
        Инициализирует менеджер задач

        :param sources: Набор источников задач
        '''
        self._sources = sources or []

    def iter_tasks(self) -> Iterable[Task]:
        '''
        Вовзвращает все задачи из всех источников,
        если источник не соответствует протоколу, то
        выбрасывает ошибку

        :return: Все задачи из всех источников
        '''
        for source in self._sources:
            if not isinstance(source, TaskSource):
                raise TypeError("Источник должен соответствовать протоколу TaskSource")
            for task in source.get_tasks():
                yield task
