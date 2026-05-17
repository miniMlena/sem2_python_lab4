import asyncio
import logging
from typing import Sequence
from src.base_classes.task import Task
from src.base_classes.task_manager import TaskManager
from src.executors.handler_protocol import TaskHandlerProtocol

logger = logging.getLogger(__name__)

class AsyncTaskExecutor:
    """
    Асинхронный исполнитель задач. Управляет пулом воркеров, которые обрабатывают задачи из очереди
    с использованием заданного обработчика.
    """
    
    def __init__(
        self,
        handler: TaskHandlerProtocol,
        workers: int = 2,
        max_queue_size: int = 0,
        name: str = "executor"
    ) -> None:
        """
        Инициализация исполнителя.
        
        :param handler: Экземпляр обработчика, реализующий TaskHandlerProtocol
        :param workers: Количество воркеров (параллельных обработчиков)
        :param max_queue_size: Максимальный размер очереди (0 - без ограничений)
        :param name: Имя исполнителя для логирования
        """
        if not isinstance(handler, TaskHandlerProtocol):
            raise TypeError(
                f"handler должен реализовывать TaskHandlerProtocol, "
                f"получен: {type(handler).__name__}"
            )
        
        if workers < 1:
            raise ValueError(f"Количество воркеров должно быть >= 1, получено: {workers}")
        
        self._handler = handler
        self._workers_count = workers
        self._max_queue_size = max_queue_size
        self._name = name
        
        self._queue: asyncio.Queue[Task] = asyncio.Queue(maxsize=max_queue_size)
        self._workers_tasks: list[asyncio.Task] = []
        self._is_running = False
        
        self._logger = logging.getLogger(f"{__name__}.{name}")
        self._stats = {
            "submitted": 0,
            "completed": 0,
            "failed": 0
        }
    
    async def __aenter__(self) -> "AsyncTaskExecutor":
        """Контекстный менеджер: запуск исполнителя"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Контекстный менеджер: остановка исполнителя."""
        await self.stop()
    
    async def start(self) -> None:
        """Запуск исполнителя: инициализация обработчика и воркеров"""
        if self._is_running:
            self._logger.warning("Исполнитель уже запущен")
            return
        
        self._logger.info(
            f"Запуск исполнителя '{self._name}': "
            f"{self._workers_count} воркеров, "
            f"обработчик: {type(self._handler).__name__}, "
            f"макс.размер очереди: {self._max_queue_size or 'безлимит'}"
        )
        if hasattr(self._handler, "setup"):
            await self._handler.setup()
            self._logger.debug("Обработчик инициализирован")

        self._workers_tasks = [
            asyncio.create_task(self._worker(worker_id=i))
            for i in range(self._workers_count)
        ]
        
        self._is_running = True
        self._logger.info("Исполнитель запущен")
    
    async def stop(self, timeout: float = 10.0) -> None:
        """
        Остановка исполнителя
        
        :param timeout: Таймаут ожидания завершения задач (в секундах)
        """
        if not self._is_running:
            self._logger.warning("Исполнитель уже остановлен")
            return
        
        self._logger.info("Остановка исполнителя...")

        try:
            await asyncio.wait_for(self._queue.join(), timeout=timeout)
            self._logger.info(f"Все задачи обработаны. Статистика: {self._stats}")
        except asyncio.TimeoutError:
            self._logger.warning(
                f"Таймаут ожидания ({timeout}с). "
                f"Осталось задач в очереди: {self._queue.qsize()}"
            )

        for worker_task in self._workers_tasks:
            worker_task.cancel()

        results = await asyncio.gather(*self._workers_tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self._logger.debug(f"Воркер {i} завершился с ошибкой: {result}")

        if hasattr(self._handler, "cleanup"):
            await self._handler.cleanup()
            self._logger.debug("Обработчик очищен")
        
        self._workers_tasks.clear()
        self._is_running = False
        self._logger.info(
            f"Исполнитель остановлен. "
            f"Итоговая статистика: {self._stats}"
        )
    
    async def submit(self, task: Task) -> None:
        """
        Добавление одной задачи в очередь.
        
        :param task: Экземпляр задачи
        """
        if not self._is_running:
            raise RuntimeError("Исполнитель не запущен. Используйте контекстный менеджер.")
        
        self._stats["submitted"] += 1
        self._logger.debug(f"Задача id={task.id} добавлена в очередь")
        await self._queue.put(task)
    
    async def submit_batch(self, tasks: Sequence[Task]) -> None:
        """
        Добавление нескольких задач в очередь.
        
        :param tasks: Последовательность задач
        """
        for task in tasks:
            await self.submit(task)
        self._logger.info(f"Добавлено {len(tasks)} задач в очередь")
    
    async def submit_from_manager(self, manager: TaskManager) -> None:
        """
        Добавление всех задач из TaskManager.
        
        :param manager: Экземпляр TaskManager с источниками задач
        """
        count = 0
        for task in manager.iter_tasks():
            await self.submit(task)
            count += 1
        
        self._logger.info(f"Загружено {count} задач из TaskManager")
    
    async def _worker(self, worker_id: int) -> None:
        """
        Воркер - асинхронная корутина, обрабатывающая задачи из очереди.
        
        :param worker_id: Идентификатор воркера для логирования
        """
        worker_logger = logging.getLogger(f"{__name__}.{self._name}.worker-{worker_id}")
        worker_logger.info(f"Воркер {worker_id} запущен")
        
        while True:
            try:
                task = await self._queue.get()
                
                worker_logger.debug(f"Воркер {worker_id} взял задачу id={task.id}")
                
                try:
                    await self._handler.handle(task)
                    self._stats["completed"] += 1
                    worker_logger.info(
                        f"Задача id={task.id} успешно обработана. "
                        f"Прогресс: {self._stats['completed']}/{self._stats['submitted']}"
                    )
                except asyncio.CancelledError:
                    # отмена задачи
                    raise
                except Exception as e:
                    # централизованная обработка ошибок
                    self._stats["failed"] += 1
                    worker_logger.error(
                        f"Ошибка при обработке задачи id={task.id}: {type(e).__name__}: {e}",
                        exc_info=True
                    )
                finally:
                    self._queue.task_done()
                    
            except asyncio.CancelledError:
                worker_logger.info(f"Воркер {worker_id} остановлен")
                break
            except Exception as e:
                worker_logger.error(f"Критическая ошибка воркера {worker_id}: {e}", exc_info=True)
                await asyncio.sleep(0.1)  # предотвращаем бесконечный цикл при ошибках
    
    @property
    def queue_size(self) -> int:
        """Текущий размер очереди"""
        return self._queue.qsize()
    
    @property
    def is_running(self) -> bool:
        """Статус исполнителя"""
        return self._is_running
    
    @property
    def stats(self) -> dict:
        """Статистика обработки"""
        return self._stats.copy()