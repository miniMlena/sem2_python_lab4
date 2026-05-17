import pytest
from datetime import datetime
from unittest.mock import patch
from src.base_classes.task import Task
from src.executors.handler_protocol import TaskHandlerProtocol
from src.executors.handlers import (
    LoggingHandler,
    PriorityBasedHandler,
    SimulateWorkHandler,
    RobustHandler,
)

#  тесты для TaskHandlerProtocol

def test_handler_protocol_accepts_correct_handler():
    """Проверяет, что протокол принимает корректный обработчик."""
    class CorrectHandler:
        async def handle(self, task: Task) -> None:
            pass
        async def setup(self) -> None:
            pass
        async def cleanup(self) -> None:
            pass
    
    handler = CorrectHandler()
    assert isinstance(handler, TaskHandlerProtocol)


def test_handler_protocol_rejects_incorrect_handler():
    """Проверяет, что протокол отклоняет некорректный обработчик."""
    class IncorrectHandler:
        pass
    
    handler = IncorrectHandler()
    assert not isinstance(handler, TaskHandlerProtocol)


# для LoggingHandler

@pytest.mark.asyncio
async def test_logging_handler_handle():
    """Тестирует, что LoggingHandler обрабатывает задачу без ошибок."""
    task = Task(id="test1", title="Test Task", author="milena", content="Test content")
    handler = LoggingHandler()

    await handler.handle(task)


@pytest.mark.asyncio
async def test_logging_handler_setup_and_cleanup():
    """Тестирует методы setup и cleanup LoggingHandler."""
    handler = LoggingHandler()
    
    await handler.setup()
    await handler.cleanup()


# для PriorityBasedHandler

@pytest.mark.asyncio
async def test_priority_handler_different_priorities():
    """Тест, что задача с высоким приоритетом обрабатывается быстрее, чем задача с низким приоритетом"""
    task = Task(id="high", title="High Priority", author="milena", content="test", priority=1)
    handler = PriorityBasedHandler()
    
    start = datetime.now()
    await handler.handle(task)
    duration = (datetime.now() - start).total_seconds()
    
    # высокий приоритет => обработк должна занимать примерно 5*0.1 = 0,5 секунд)
    assert duration >= 0.5

    task = Task(id="low", title="Low Priority", author="milena", content="test", priority=5)
    handler = PriorityBasedHandler()
    
    start = datetime.now()
    await handler.handle(task)
    duration = (datetime.now() - start).total_seconds()
    
    # низкий приоритет => обрабатывается примерно 0.1 секунд
    assert duration < 0.5


# для SimulateWorkHandler

@pytest.mark.asyncio
async def test_simulate_work_handler_updates_status():
    """Тест, что SimulateWorkHandler обновляет статус задачи"""
    task = Task(id="work2", title="Work Task", author="milena", content="test")
    handler = SimulateWorkHandler(base_delay=0.1, jitter=0.0)
    
    assert task.status.value == "pending"
    
    await handler.handle(task)
    
    assert task.status.value == "done"
    assert task.completed_at is not None


# тесты для RobustHandler

@pytest.mark.asyncio
async def test_robust_handler_success():
    """Тестирует успешную обработку задачи без ошибок."""
    task = Task(id="robust1", title="Robust Task", author="milena", content="test")
    handler = RobustHandler(fail_probability=0.0, max_retries=2)
    
    await handler.handle(task)
    
    assert task.status.value == "done"


@pytest.mark.asyncio
async def test_robust_handler_retry_on_failure():
    """Тестирует, что обработчик делает повторные попытки при ошибке."""
    task = Task(id="robust2", title="Robust Task", author="milena", content="test")
    
    # создаем мок, который падает 2 раза, затем завершается успешно
    mock_handler = RobustHandler(fail_probability=0.0, max_retries=2)
    
    with patch('random.random', side_effect=[0.1, 0.1, 0.9]):
        await mock_handler.handle(task)
    
    assert task.status.value == "done"
    assert task.id not in mock_handler._attempts


@pytest.mark.asyncio
async def test_robust_handler_max_retries_exceeded():
    """Тест, что обработчик выбрасывает исключение после превышения попыток."""
    task = Task(id="robust3", title="Robust Task", author="milena", content="test")
    handler = RobustHandler(fail_probability=1.0, max_retries=2)
    
    with pytest.raises(RuntimeError, match="Симуляция ошибки"):
        await handler.handle(task)
