import pytest
from typing import List, Iterator
from src.base_classes.task import Task
from src.base_classes.enums import TaskPriority
from src.base_classes.task_manager import TaskManager
from src.base_classes.task_queue import TaskQueue

# фиксатуры и моки для тестов

@pytest.fixture
def sample_tasks() -> List[Task]:
    """Создает набор тестовых задач с разными статусами и приоритетами"""
    tasks = [
        Task(
            id="1",
            title="Простая задача",
            author="Миша",
            content="Сделать что-то",
            priority=TaskPriority.MEDIUM,
        ),
        Task(
            id="2",
            title="Срочная задача",
            author="Милена",
            content="Срочно сделать",
            priority=TaskPriority.URGENT,
        ),
        Task(
            id="3",
            title="Завершенная задача",
            author="Миша",
            content="Уже сделано",
            priority=TaskPriority.LOW,
        ),
        Task(
            id="4",
            title="Критическая задача",
            author="Лиза",
            content="Критично важно",
            priority=TaskPriority.CRITICAL,
        ),
        Task(
            id="5",
            title="Задача на проверке",
            author="Милена",
            content="Проверить",
            priority=TaskPriority.HIGH,
        ),
    ]
    tasks[1].start()
    tasks[2].start()
    tasks[2].complete()
    tasks[4].start()
    tasks[4].review()
    return tasks

class MockTaskManager(TaskManager):
    """Мок менеджера задач."""
    def __init__(self, tasks: List[Task]):
        self._tasks = tasks
    
    def iter_tasks(self) -> Iterator[Task]:
        for task in self._tasks:
            yield task

@pytest.fixture
def task_manager(sample_tasks) -> TaskManager:
    """Создает менеджер задач с тестовыми данными"""
    return MockTaskManager(sample_tasks)

@pytest.fixture
def task_queue(task_manager) -> TaskQueue:
    """Создает очередь задач"""
    return TaskQueue(task_manager)