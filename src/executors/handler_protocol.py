from typing import Protocol, runtime_checkable
from src.base_classes.task import Task

@runtime_checkable
class TaskHandlerProtocol(Protocol):
    """Протокол для асинхронных обработчиков задач"""
    
    async def handle(self, task: Task) -> None:
        """
        Асинхронная обработка задачи
        
        :param task: Экземпляр задачи для обработки
        """
        ...
    
    async def setup(self) -> None:
        """
        Опциональный метод для инициализации обработчика.
        Вызывается исполнителем при старте.
        """
        ...
    
    async def cleanup(self) -> None:
        """
        Опциональный метод для освобождения ресурсов.
        Вызывается исполнителем при остановке.
        """
        ...