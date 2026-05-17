import asyncio
import logging
from pathlib import Path
import random
from datetime import datetime
from src.base_classes.task import Task
from src.executors.handler_protocol import TaskHandlerProtocol

Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),  # в консоль
        logging.FileHandler(f"logs/app_{datetime.now().strftime('%Y%m%d')}.log", encoding='utf-8')  # в файл
    ]
)

logger = logging.getLogger(__name__)

class LoggingHandler(TaskHandlerProtocol):
    """
    Базовый обработчик с логированием начала и завершения
    """
    
    async def handle(self, task: Task) -> None:
        """Логирует начало и окончание обработки."""
        logger.info(f"[LoggingHandler] Начало обработки: {task.id} - '{task.title}'")
        
        await asyncio.sleep(0.1)
        
        logger.info(f"[LoggingHandler] Завершена обработка: {task.id}")
    
    async def setup(self) -> None:
        logger.debug("LoggingHandler: инициализация")
    
    async def cleanup(self) -> None:
        logger.debug("LoggingHandler: очистка")


class PriorityBasedHandler(TaskHandlerProtocol):
    """
    Обработчик с задержкой, зависящей от приоритета задачи
    """
    
    async def handle(self, task: Task) -> None:
        """Обрабатывает задачу с задержкой, пропорциональьной приоритету"""
        delay = (6 - task.priority) * 0.1
        
        logger.info(
            f"[PriorityHandler] Задача '{task.id}' (приоритет={task.priority}) "
            f"требует {delay:.2f}с обработки"
        )
        
        await asyncio.sleep(delay)

        task.start()
        await asyncio.sleep(delay * 0.5)
        task.complete()
        
        logger.info(f"[PriorityHandler] Задача '{task.id}' завершена за {delay:.2f}с")


class SimulateWorkHandler(TaskHandlerProtocol):
    """
    Обработчик, имитирующий реальную работу с случайной длительностью обработки
    """
    
    def __init__(self, base_delay: float = 0.5, jitter: float = 0.2):
        """
        :param base_delay: Базовая задержка в секундах
        :param jitter: Случайное отклонение
        """
        self._base_delay = base_delay
        self._jitter = jitter
    
    async def handle(self, task: Task) -> None:
        """Имитирует работу с случайной длительностью"""
        actual_delay = self._base_delay + random.uniform(-self._jitter, self._jitter)
        actual_delay = max(0.1, actual_delay)
        
        logger.info(
            f"[WorkHandler] Задача '{task.id}' начала выполнение "
            f"(ожидается {actual_delay:.2f}с)"
        )
        task.start()
        
        steps = 3
        for i in range(steps):
            await asyncio.sleep(actual_delay / steps)
            logger.debug(f"[WorkHandler] Задача '{task.id}': шаг {i+1}/{steps}")
        
        task.complete()
        logger.info(f"[WorkHandler] Задача '{task.id}' выполнена")


class RobustHandler(TaskHandlerProtocol):
    """
    Обработчик с встроенной обработкой ошибок и повторными попытками.
    Демонстрирует, как обработчик может самостоятельно управлять ошибками
    """
    
    def __init__(self, fail_probability: float = 0.2, max_retries: int = 2):
        """
        :param fail_probability: Вероятность ошибки (0.0-1.0)
        :param max_retries: Максимальное количество повторных попыток
        """
        self._fail_probability = fail_probability
        self._max_retries = max_retries
        self._attempts = {}
    
    async def handle(self, task: Task) -> None:
        """Обрабатывает задачу с возможными ошибками и повторными попытками."""
        task_id = task.id
        
        if task_id not in self._attempts:
            self._attempts[task_id] = 0
        
        self._attempts[task_id] += 1

        if random.random() < self._fail_probability and self._attempts[task_id] <= self._max_retries:
            logger.warning(
                f"[RobustHandler] Задача '{task_id}': попытка {self._attempts[task_id]} "
                f"завершилась ошибкой (будет повтор)"
            )
            raise RuntimeError(f"Симуляция ошибки при обработке задачи {task_id}")
        
        logger.info(
            f"[RobustHandler] Задача '{task_id}' успешно обработана "
            f"(попытка {self._attempts[task_id]})"
        )
        
        task.start()
        await asyncio.sleep(0.3)
        task.complete()
        
        del self._attempts[task_id]
    
    async def cleanup(self) -> None:
        """Очищает внутреннее состояние."""
        self._attempts.clear()
        logger.debug("RobustHandler: состояние очищено")
