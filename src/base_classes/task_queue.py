from collections.abc import Iterable, Iterator, Callable
from typing import Any
from src.base_classes.task import Task
from src.base_classes.enums import TaskStatus
from src.base_classes.task_manager import TaskManager


class TaskQueueIterator(Iterator[Task]):
    """Итератор с поддержкой ленивого кэширования"""
    def __init__(self, queue: "TaskQueue"):
        self._queue = queue
        self._index = 0
        self._source_exhausted = False

    # протокол итератора:

    def __iter__(self):
        return self

    def __next__(self) -> Task:
        # если задача есть в кэшэ, возвращаем ее оттуда
        if self._index < len(self._queue._cache):
            task = self._queue._cache[self._index]
            self._index += 1
            return task

        if self._source_exhausted or self._queue._fully_consumed:
            raise StopIteration

        # читаем следующую задачу из источника, возможно в кэше они ещё не появились
        try:
            task = next(self._queue._task_iterator)
            self._queue._cache.append(task)
            self._index += 1
            return task
        except StopIteration:
            self._source_exhausted = True
            self._queue._fully_consumed = True
            raise


class TaskQueue:
    """
    Очередь задач с поддержкой многократной итерации, ленивых фильтров
    и потоковой обработки.
    """
    def __init__(self, manager: "TaskManager"):
        self._manager: "TaskManager" = manager
        self._cache: list[Task] = []
        self._fully_consumed: bool = False
        self._task_iterator: Iterator[Task] | None = None

    def __iter__(self) -> Iterator[Task]:
        if self._task_iterator is None and not self._fully_consumed:
            self._task_iterator = iter(self._manager.iter_tasks())
        return TaskQueueIterator(self)

    def filter(self, predicate: Callable[[Task], bool]) -> Iterable[Task]:
        """Ленивый фильтр"""
        for task in self:
            if predicate(task):
                yield task

    # готовые фильтры:

    def filter_by_status(self, status: TaskStatus | str) -> Iterable[Task]:
        """Фильтр по """
        if isinstance(status, str):
            status = TaskStatus(status.lower())

        return self.filter(lambda t: t.status == status)

    def filter_by_priority(self, min_priority: int = 1, max_priority: int = 5) -> Iterable[Task]:
        """Фильтр по диапазону приоритетов"""
        return self.filter(lambda t: min_priority <= t.priority <= max_priority)

    def filter_by_author(self, author: str) -> Iterable[Task]:
        """Фильтр по автору"""
        author_lower = author.strip().lower()
        return self.filter(lambda t: t.author.lower() == author_lower)

    def filter_by_title_contains(self, substring: str) -> Iterable[Task]:
        """Фильтр по подстроке в названии"""
        substring_lower = substring.lower()
        return self.filter(lambda t: substring_lower in t.title.lower())

    def pending(self) -> Iterable[Task]:
        """Фильтр по статусу 'pending'"""
        return self.filter_by_status(TaskStatus.PENDING)

    def in_progress(self) -> Iterable[Task]:
        """Фильтр по статусу 'in_progress'"""
        return self.filter_by_status(TaskStatus.IN_PROGRESS)

    def done(self) -> Iterable[Task]:
        """Фильтр по статусу 'done'"""
        return self.filter_by_status(TaskStatus.DONE)

    def high_priority(self) -> Iterable[Task]:
        """Фильтр по высокому приоритету"""
        return self.filter_by_priority(min_priority=4)

    def process(self, processor: Callable[[Task], Any] = lambda x: x) -> Iterable[Any]:
        """
        Потоковая обработка задач (по умолчанию просто выдает задачи)
        
        :param processor: функция преобразования задач (по умолчанию ничего не меняет)
        :return: Генератор задач
        """
        for task in self:
            yield processor(task)

    def __repr__(self) -> str:
        cached = len(self._cache)
        status = " (источник полностью обработан)" if self._fully_consumed else " (+ недообработанный источник)"
        return f"Количество задач в очереди: ({cached} кэшировано{status})"

    def reset(self) -> None:
        """Сброс кэша"""
        self._cache.clear()
        self._fully_consumed = False
        self._task_iterator = None