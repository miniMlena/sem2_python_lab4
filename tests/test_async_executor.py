import asyncio
import pytest
from datetime import datetime
from src.base_classes.task import Task
from src.base_classes.task_manager import TaskManager
from src.base_classes.task_source import TaskSource
from src.executors.async_executor import AsyncTaskExecutor
from src.executors.handler_protocol import TaskHandlerProtocol
from src.executors.handlers import (
    LoggingHandler,
    SimulateWorkHandler,
)

@pytest.mark.asyncio
async def test_executor_creation():
    """Тестируем создание исполнителя с корректными параметрами."""
    handler = LoggingHandler()
    executor = AsyncTaskExecutor(handler, workers=3, name="test")
    
    assert executor._workers_count == 3
    assert executor._name == "test"
    assert executor.is_running is False
    assert executor.stats["submitted"] == 0


def test_executor_creation_invalid_handler():
    """Тест, что создание исполнителя с неверным обработчиком вызывает ошибку"""
    class InvalidHandler:
        pass
    
    handler = InvalidHandler()
    
    with pytest.raises(TypeError, match="handler должен реализовывать TaskHandlerProtocol"):
        AsyncTaskExecutor(handler)


@pytest.mark.asyncio
async def test_executor_context_manager():
    """Тестирует работу контекстного менеджера"""
    handler = LoggingHandler()
    
    async with AsyncTaskExecutor(handler, workers=2) as executor:
        assert executor.is_running is True
    
    assert executor.is_running is False


@pytest.mark.asyncio
async def test_executor_submit_batch():
    """Тестирует добавление нескольких задач в очередь"""
    handler = LoggingHandler()
    tasks = [
        Task(id=f"batch{i}", title=f"Task{i}", author="milena", content="test")
        for i in range(5)
    ]
    
    async with AsyncTaskExecutor(handler, workers=3) as executor:
        await executor.submit_batch(tasks)
        await asyncio.sleep(0.5)
    
    assert executor.stats["submitted"] == 5
    assert executor.stats["completed"] == 5


@pytest.mark.asyncio
async def test_executor_error_handling():
    """Тестирует централизованную обработку ошибок"""
    class ErrorHandler(TaskHandlerProtocol):
        async def handle(self, task: Task) -> None:
            raise ValueError("Test error")
        async def setup(self) -> None:
            pass
        async def cleanup(self) -> None:
            pass
    
    handler = ErrorHandler()
    task = Task(id="error1", title="error Task", author="milena", content="test")
    
    async with AsyncTaskExecutor(handler, workers=1) as executor:
        await executor.submit(task)
        await asyncio.sleep(0.2)
    
    assert executor.stats["submitted"] == 1
    assert executor.stats["completed"] == 0
    assert executor.stats["failed"] == 1


@pytest.mark.asyncio
async def test_executor_stop_timeout():
    """Тестирует остановку с таймаутом."""
    class SlowHandler(TaskHandlerProtocol):
        async def handle(self, task: Task) -> None:
            await asyncio.sleep(1.0)
        async def setup(self) -> None:
            pass
        async def cleanup(self) -> None:
            pass
    
    handler = SlowHandler()
    executor = AsyncTaskExecutor(handler, workers=1)
    task = Task(id="slow1", title="Slow", author="milena", content="test")
    
    await executor.start()
    await executor.submit(task)
    
    await executor.stop(timeout=0.1)
    
    assert executor.is_running is False


@pytest.mark.asyncio
async def test_executor_submit_from_manager():
    """Тестирует загрузку задач из TaskManager."""
    handler = LoggingHandler()
    
    # мок источника задач
    class MockTaskSource(TaskSource):
        def get_tasks(self):
            return [
                Task(id=f"source{i}", title=f"Source{i}", author="milena", content="test")
                for i in range(3)
            ]
    
    source = MockTaskSource()
    manager = TaskManager(sources=[source])
    
    async with AsyncTaskExecutor(handler, workers=2) as executor:
        await executor.submit_from_manager(manager)
        await asyncio.sleep(0.3)
    
    assert executor.stats["submitted"] == 3
    assert executor.stats["completed"] == 3


@pytest.mark.asyncio
async def test_executor_multiple_workers_parallel():
    """Тестирует параллельную обработку задач несколькими воркерами"""
    handler = SimulateWorkHandler(base_delay=0.2, jitter=0.0)
    tasks = [
        Task(id=f"parallel{i}", title=f"title_{i}", author="milena", content="test")
        for i in range(4)
    ]
    
    start = datetime.now()
    async with AsyncTaskExecutor(handler, workers=4) as executor:
        await executor.submit_batch(tasks)
        while executor.queue_size > 0:
            await asyncio.sleep(0.05)
    duration = (datetime.now() - start).total_seconds()

    # время обработки при 2 воркерах должно быть меньше
    assert duration < 0.5


@pytest.mark.asyncio
async def test_executor_handles_setup_and_cleanup():
    """Тестирует, что executor вызывает setup и cleanup обработчика"""
    class HandlerWithTracking(TaskHandlerProtocol):
        def __init__(self):
            self.setup_called = False
            self.cleanup_called = False
        
        async def handle(self, task: Task) -> None:
            pass
        
        async def setup(self) -> None:
            self.setup_called = True
        
        async def cleanup(self) -> None:
            self.cleanup_called = True
    
    handler = HandlerWithTracking()
    
    async with AsyncTaskExecutor(handler, workers=1) as executor:
        assert handler.setup_called is True
        assert handler.cleanup_called is False
    
    assert handler.cleanup_called is True