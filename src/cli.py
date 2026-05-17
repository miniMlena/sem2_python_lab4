import asyncio
from datetime import datetime
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import typer
from typer import Typer
from src.base_classes.task import Task
from src.base_classes.task_manager import TaskManager
from src.base_classes.task_queue import TaskQueue
from src.sources.registry import REGISTRY
from src.executors.async_executor import AsyncTaskExecutor
from src.executors.handlers import (
    LoggingHandler,
    PriorityBasedHandler,
    SimulateWorkHandler,
    RobustHandler,
)

# хранилище задач (для демонстрации)
tasks_storage: Dict[str, Task] = {}

# Глобальная очередь (создаётся один раз)
task_queue: TaskQueue | None = None

cli = Typer(add_help_option=False, add_completion=False)


def display_task_info(task: Task) -> None:
    """Отображает информацию о задаче"""
    data = task.to_dict()

    print(f"Информация о задаче {data['id']}")
    print(f"ID:          {data['id']}")
    print(f"Название:    {data['title']}")
    print(f"Автор:       {data['author']}")
    print(f"Содержание:  {data['content']}")
    print(f"Приоритет:   {data['priority']} ({data['priority_label']})")
    print(f"Статус:      {data['status']}")
    print(f"Создана:     {data['created_at']}")
    print(f"Начата:      {data['started_at'] or 'Не начата'}")
    print(f"Завершена:   {data['completed_at'] or 'Не завершена'}")
    print(f"Возраст:     {data['age_seconds']:.1f} сек.")
    print(f"Длительность: {data['work_duration']:.1f} сек." if data['work_duration'] else "Длительность: Не завершена")


def display_all_tasks() -> None:
    """Отображает список всех задач"""
    if not tasks_storage:
        print("Нет созданных задач")
        return
    
    print("\n" + "-" * 90)
    print(f"{'ID':<15} {'Название':<30} {'Автор':<15} {'Статус':<15} {'Приоритет':<10}")
    print("-" * 90)
    
    for task in tasks_storage.values():
        title_display = task.title[:27] + "..." if len(task.title) > 30 else task.title
        print(f"{task.id:<15} {title_display:<30} {task.author:<15} {str(task.status):<15} {task.priority} ({task.priority_label})")
    
    print(f"Всего задач: {len(tasks_storage)}\n")


def get_task_or_exit(task_id: str) -> Optional[Task]:
    """Получает задачу по ID или выводит сообщение об ошибке"""
    if task_id not in tasks_storage:
        print(f"Ошибка: Задача с ID '{task_id}' не найдена")
        return None
    return tasks_storage[task_id]


def build_sources(stdin: bool, jsonl: list[Path]) -> list[Any]:
    """Создает источники задач"""
    sources: list[Any] = []
    for path in jsonl:
        sources.append(REGISTRY["jsonl-file"](path))
    if stdin:
        sources.append(REGISTRY["stdin"]())
    return sources

@cli.command("instruct")
def display_instructions() -> None:
    """Показывает подробную инструкцию по использованию"""
    print("""
Доступные команды:

1. instruct - Выводит это сообщение
    У этой команды нет опций или аргументов
    Пример: instruct

2. sources - Выводит список доступных источников задач
   Пример: sources

3. read - Читает и показывает задачи из указанных источников с возможностью фильтрации
    Аргументы и опции:
     --stdin              - Считывать задачи из стандартного ввода
     --max-tasks N        - Максимальное число задач (0 = без ограничения)
     --author TEXT        - Фильтр по автору
     --contains TEXT      - Фильтр по содержанию
     file1.jsonl          - Пути к JSONL файлам
    
    Подробно про аргументы и опции команды read:
          
    В качестве аргументов можно указать файлы формата jsonl, тогда задачи будут читаться из них.
    Примеры:
    read example_1.jsonl
    read example_1.jsonl example_2.jsonl
          
    --stdin - Считывать задачи из сдандартного ввода
    Задачи нужно писать в формате id:title:author:content:priority(число)
    Если вы захотите перестать вводить задачи, напишите stop
    Пример использования:
    read --stdin
    Дальше вводим задачи, например:   my_id:my_title:my_author:my_content:1
          
    --max_tasks - Установить максимум, сколько задач может быть прочитано
    По умолчанию 10, если поставить 0, то можно прочитать неограниченное число задач.
    При одновременном вводе --max_tasks 0 и --stdin не забывайте про возможность завершить ввод задач командой stop.
    Примеры:
    read --stdin --max-tasks 5
    read example_1.jsonl --max-tasks 0
          
    --author - Считывать задачи только указанного автора
    Пример:
    read --stdin --author milena
    Все встреченные задачи с другим автором не будут считываться программой
          
    --contains - Считывать только задачи с указанной подстрокой в содержании
    Пример:
    read example_1.jsonl --contains проект
    Задача '8:Сделать бэкап:milena:Сделать бэкап базы данных проекта:2' будет считана")
    Задача '9:Написать тесты:cool_user:Написать тесты к лабе по python:3' не считается")
          
    Все аргументы и опции можно комбинировать, примеры:
    read example_1.jsonl example_2.jsonl --max-tasks 20 --author kate
    read example_1.jsonl example_2.jsonl --stdin --max-tasks 20
    read example_1.jsonl --stdin --author alina --contains python

4. start TASK_ID - Начинает выполнение задачи
   Пример: start T-001

5. review TASK_ID - Отправляет задачу на ревью
   Пример: review PY_002

6. complete TASK_ID - Завершает задачу
   Пример: complete C_006

7. archive TASK_ID - Архивирует задачу
   Пример: archive T-007

8. info TASK_ID - Показывает подробную информацию о задаче
   Пример: info A111

9. list - Показывает список всех задач
   Пример: list

10. create - Создает новую задачу в интерактивном режиме
    Пример: create

11. queue-init - Создание очереди с указанными источниками
    Аргументами являются jsonl-файлы. Очередь единая на всю программу, при повторном вводе этой команды очередь перезаписывается.
    Пример:
    queue-init example_1.jsonl
          
12. queue-demo - Быстро демонстрирует основные операции с очередью
    Пример: queue-demo
          
13. queue-filter - Фильтрует задачи в очереди по указанным критериям
    Опции:
    --status - фильтр по статусу
    --min_priority - фильтр по минимальному приоритету
    --author - фильтр по автору
    --contains - фильтр по подстроке в названии задчи
    Опции можно комбинировать.
    Примеры:
    queue-filter --contains дз
    queue-filter --author kate --status done
    queue-filter --min-priority 2 --author milena --contains от
          
14. queue-process - Демонстрирует потоковую обработку задач
    Пример: queue-process
          
15. async-demo - Демонстрация работы асинхронного обработчика
    Пример: async-demo

16. async-interactive - Переход в режим интерактивной асинхронной обработки.
    В этом режиме доступно несколько команд:
        add <id> <title> [priority]  - Добавить задачу
        add-test <n>                 - Добавить n тестовых задач
        status                       - Показать статус обработки
        workers <n>                  - Изменить количество воркеров (будет перезапуск)
        handler <type>               - Сменить обработчика (logging/priority/work/robust)
        stop                         - Остановить обработку и выйти
    Пример:
    async-interactive
    add-test 8
    status
    stop
          
17. exit - Выход из программы
    Пример: exit

""")


@cli.command("sources")
def list_sources() -> None:
    """Выводит список доступных источников"""
    print("Доступные источники:")
    for name in sorted(REGISTRY):
        print(f"  - {name}")

@cli.command("read")
def read_tasks(
    stdin: bool = typer.Option(False, "--stdin", help="Прочитать задачи из стандартного ввода"),
    jsonl: list[Path] = typer.Argument(
        None,
        help="Прочитать задачи из JSONL файлов",
    ),
    max_tasks: int = typer.Option(
        10,
        "--max-tasks",
        help="Максимальное число задач (0 = без ограничения)",
        min=0,
    ),
    author: Optional[str] = typer.Option(None, "--author", help="Читать задачи только от заданного автора"),
    contains: Optional[str] = typer.Option(None, "--contains", help="Читать только задачи, содержащие заданную подстроку"),
) -> None:
    """Читает задачи из указанных источников"""
    if not stdin and not jsonl:
        print("Ошибка: Укажите хотя бы один источник (--stdin или JSONL файлы)")
        return
    
    if jsonl is None:
        jsonl = []
    
    try:
        raw_sources = build_sources(stdin, jsonl)
        inbox = TaskManager(raw_sources)
        count = 0
        
        for tsk in inbox.iter_tasks():
            if author and author != tsk.author:
                continue
            if contains and contains not in tsk.content:
                continue
            
            if tsk.id in tasks_storage:
                print(f"Предупреждение: Задача с ID '{tsk.id}' уже существует, пропускаем")
                continue
            
            tasks_storage[tsk.id] = tsk
            count += 1
            print(f"Создана задача: {tsk}")
            
            if max_tasks and count >= max_tasks:
                break
        
        print(f"\nВсего создано задач: {count}")
        
    except Exception as e:
        print(f"Ошибка при чтении задач: {e}")


@cli.command("start")
def start_task(task_id: str = typer.Argument(..., help="ID задачи")) -> None:
    """Начинает выполнение задачи"""
    task = get_task_or_exit(task_id)
    if not task:
        return
    
    try:
        old_status = task.status
        task.start()
        print(f"Задача '{task_id}' переведена из статуса '{old_status}' в '{task.status}'")
    except Exception as e:
        print(f"Ошибка: {e}")


@cli.command("review")
def review_task(task_id: str = typer.Argument(..., help="ID задачи")) -> None:
    """Отправляет задачу на ревью"""
    task = get_task_or_exit(task_id)
    if not task:
        return
    
    try:
        old_status = task.status
        task.review()
        print(f"Задача '{task_id}' переведена из статуса '{old_status}' в '{task.status}'")
    except Exception as e:
        print(f"Ошибка: {e}")


@cli.command("complete")
def complete_task(task_id: str = typer.Argument(..., help="ID задачи")) -> None:
    """Завершает задачу"""
    task = get_task_or_exit(task_id)
    if not task:
        return
    
    try:
        old_status = task.status
        task.complete()
        print(f"Задача '{task_id}' переведена из статуса '{old_status}' в '{task.status}'")
    except Exception as e:
        print(f"Ошибка: {e}")


@cli.command("archive")
def archive_task(task_id: str = typer.Argument(..., help="ID задачи")) -> None:
    """Архивирует задачу"""
    task = get_task_or_exit(task_id)
    if not task:
        return
    
    try:
        old_status = task.status
        task.archive()
        print(f"Задача '{task_id}' переведена из статуса '{old_status}' в '{task.status}'")
    except Exception as e:
        print(f"Ошибка: {e}")


@cli.command("info")
def task_info(task_id: str = typer.Argument(..., help="ID задачи")) -> None:
    """Показывает подробную информацию о задаче"""
    task = get_task_or_exit(task_id)
    if not task:
        return
    
    display_task_info(task)


@cli.command("list")
def list_all_tasks() -> None:
    """Показывает список всех задач"""
    display_all_tasks()


@cli.command("create")
def create_task_interactive() -> None:
    """Создает новую задачу в интерактивном режиме"""
    print("    Создание новой задачи:")

    while True:
        task_id = input("ID задачи: ").strip()
        if task_id in tasks_storage:
            print("Ошибка: Задача с таким ID уже существует!")
            continue
        if not task_id:
            print("Ошибка: ID не может быть пустым!")
            continue
        break

    while True:
        title = input("Название задачи: ").strip()
        if len(title) < 3:
            print("Ошибка: Название должно содержать минимум 3 символа!")
            continue
        break

    while True:
        author = input("Автор: ").strip()
        if len(author) < 2:
            print("Ошибка: Имя автора должно содержать минимум 2 символа!")
            continue
        break

    while True:
        content = input("Содержание задачи: ").strip()
        if not content:
            print("Ошибка: Содержание не может быть пустым!")
            continue
        break

    print("\nВыберите приоритет:")
    print("  1 - Низкий (LOW)")
    print("  2 - Средний (MEDIUM)")
    print("  3 - Высокий (HIGH)")
    print("  4 - Срочный (URGENT)")
    print("  5 - Критический (CRITICAL)")
    
    while True:
        priority_choice = input("Введите номер приоритета от 1 до 5 (по умолчанию 2): ").strip()
        if not priority_choice:
            priority_value = 2
            break
        try:
            priority_value = int(priority_choice)
            if 1 <= priority_value <= 5:
                break
            else:
                print("Ошибка: Введите число от 1 до 5")
        except ValueError:
            print("Ошибка: Введите число")
    
    try:
        task = Task(
            id=task_id,
            title=title,
            author=author,
            content=content,
            priority=priority_value
        )
        tasks_storage[task_id] = task
        print("Задача успешно создана: ")
        display_task_info(task)
    except Exception as e:
        print(f"Ошибка при создании задачи: {e}")


@cli.command("queue-init")
def initialize_queue(
    jsonl: list[Path] = typer.Argument(None, help="JSONL файлы"),
) -> None:
    """Инициализирует TaskQueue из выбранных источников"""
    global task_queue
    
    if not jsonl:
        print("Ошибка: Укажите JSONL файлы как источники для очереди")
        return
    
    if jsonl is None:
        jsonl = []
    
    sources = build_sources(False, jsonl)
    manager = TaskManager(sources)
    task_queue = TaskQueue(manager)
    print("TaskQueue успешно инициализирована!")


@cli.command("queue-demo")
def demonstrate_queue() -> None:
    """Быстро демонстрирует возможности TaskQueue"""
    global task_queue
    if task_queue is None:
        print("Сначала выполните: queue-init")
        return
    
    print("\n1) Первый проход по очереди (ленивый):")
    for task in task_queue:
        title_display = task.title[:27] + "..." if len(task.title) > 30 else task.title
        print(f"{task.id:<15} {title_display:<30} {task.author:<15} {str(task.status):<15} {task.priority} ({task.priority_label})")

    print("\n2) Повторный проход по той же очереди (из кэша), на примере функции sum:")
    count = sum(1 for _ in task_queue)
    print(f"    Всего задач в очереди: {count}")

    print("\n3) Ленивый фильтр (на примере приоритета):")
    high = list(task_queue.filter_by_priority(2, 2))
    print(f"    Задач со средним приоритетом: {len(high)}")

    print("\n4) Потоковая обработка:")
    print("    Используйте команду 'queue-process' для демонстрации")

    print(f"\nТекущее состояние: {task_queue}")


@cli.command("queue-filter")
def filter_queue(
    status: Optional[str] = typer.Option(None, "--status"),
    min_priority: Optional[int] = typer.Option(None, "--min-priority"),
    author: Optional[str] = typer.Option(None, "--author"),
    contains: Optional[str] = typer.Option(None, "--contains"),
) -> None:
    """Фильтрация задач через TaskQueue"""
    global task_queue
    if task_queue is None:
        print("Сначала выполните: queue-init")
        return

    result = task_queue

    if status:
        result = list(task_queue.filter_by_status(status))
    if min_priority is not None:
        result = [t for t in list(task_queue.filter_by_priority(min_priority=min_priority)) if t in result]
    if author:
        result = [t for t in list(task_queue.filter_by_author(author)) if t in result]
    if contains:
        result = [t for t in list(task_queue.filter_by_title_contains(contains))if t in result]

    tasks = list(result)
    print(f"\nНайдено задач: {len(tasks)}")
    
    for task in tasks:
        title_display = task.title[:27] + "..." if len(task.title) > 30 else task.title
        print(f"{task.id:<15} {title_display:<30} {task.author:<15} {str(task.status):<15} {task.priority} ({task.priority_label})")


@cli.command("queue-process")
def queue_process_demo() -> None:
    """Демонстрирует потоковую обработку задач"""
    global task_queue
    if task_queue is None:
        print("Сначала выполните: queue-init")
        return

    print("\n1) Потоковая обработка: извлекаем id, название и приоритет")
    for item in task_queue.process(lambda t: (t.id, t.title, t.priority)):
        print(f"    {item}")

    print("\n2) Подсчёт задач по приоритету через sum (ленивая обработка):")
    priority_sum = sum(
        task.priority 
        for task in task_queue.filter_by_priority(min_priority=3)
    )
    print(f"    Сумма приоритетов задач с приоритетом >= 3: {priority_sum}")

    print("\n3) Преобразование в словарь")
    dicts = list(task_queue.process(lambda t: t.to_dict()))
    print(f"    Преобразовано в словари {len(dicts)} задач:")
    for d in dicts:
        print(d)


@cli.command("async-demo")
def async_demo() -> None:
    """Демонстрирует базовую асинхронную обработку задач"""
    if not tasks_storage:
        print("Нет задач для обработки. Сначала создайте задачи через 'create' или 'read'")
        return
    
    print("\nДемонстрация асинхронной обработки задач\n")
    print(f"Доступно задач для обработки: {len(tasks_storage)}")
    print("Выберите тип обработчика:")
    print("  1 - LoggingHandler (простое логирование)")
    print("  2 - PriorityBasedHandler (зависимость от приоритета)")
    print("  3 - SimulateWorkHandler (имитация реальной работы)")
    print("  4 - RobustHandler (с обработкой ошибок)")
    
    choice = input("Ваш выбор (1-4): ").strip()
    
    handlers = {
        "1": LoggingHandler(),
        "2": PriorityBasedHandler(),
        "3": SimulateWorkHandler(base_delay=0.3),
        "4": RobustHandler(fail_probability=0.2, max_retries=2),
    }
    
    handler = handlers.get(choice)
    if not handler:
        print("Неверный выбор, используем LoggingHandler")
        handler = LoggingHandler()
    
    workers = input("Количество воркеров (по умолчанию 2): ").strip()
    workers = int(workers) if workers.isdigit() else 2

    tasks = list(tasks_storage.values())
    
    print(f"\nЗапуск асинхронной обработки {len(tasks)} задач...")
    
    async def run_demo():
        async with AsyncTaskExecutor(handler, workers=workers, name="cli-demo") as executor:
            await executor.submit_batch(tasks)
            await asyncio.sleep(0.5)
            while executor.queue_size > 0:
                await asyncio.sleep(0.5)
        
        print("\n")
        print("Статистика обработки:")
        print(f"  Всего отправлено: {executor.stats['submitted']}")
        print(f"  Успешно обработано: {executor.stats['completed']}")
        print(f"  С ошибками: {executor.stats['failed']}")
    
    asyncio.run(run_demo())


@cli.command("async-interactive")
def async_interactive() -> None:
    """
    Интерактивный режим асинхронной обработки.
    Позволяет в реальном времени добавлять задачи в очередь и наблюдать за их обработкой.
    """
    print("\nИнтерактивный режим асинхронной обработки\n")
    print("Вы можете добавлять задачи, и они будут обрабатываться в реальном времени.")
    print("Команды:")
    print("  add <id> <title> [priority]  - Добавить задачу")
    print("  add-test <n>                 - Добавить n тестовых задач")
    print("  status                       - Показать статус обработки")
    print("  workers <n>                  - Изменить количество воркеров (будет перезапуск)")
    print("  handler <type>               - Сменить обработчика (logging/priority/work/robust)")
    print("  stop                         - Остановить обработку и выйти")
    print()
    
    current_workers = 2
    current_handler = LoggingHandler()
    executor = None
    executor_task = None
    running = True
    
    handlers_map = {
        "logging": LoggingHandler,
        "priority": PriorityBasedHandler,
        "work": lambda: SimulateWorkHandler(base_delay=0.2),
        "robust": lambda: RobustHandler(fail_probability=0.2, max_retries=2),
    }
    
    async def run_executor():
        nonlocal executor
        while running:
            try:
                async with AsyncTaskExecutor(current_handler, workers=current_workers, name="interactive") as exec_instance:
                    executor = exec_instance
                    print(f"\nИсполнитель запущен: {current_workers} воркеров, обработчик={type(current_handler).__name__}")
                    # ждем, пока не будет сигнала к остановке
                    while running:
                        await asyncio.sleep(0.5)
                        if executor and executor.queue_size > 0:
                            # проказываем статус каждые 2 секунды
                            if int(datetime.now().timestamp()) % 4 < 0.5:
                                print(f"\rВ очереди: {executor.queue_size} | Обработано: {executor.stats['completed']} | Ошибок: {executor.stats['failed']}", end="", flush=True)
            except Exception as e:
                print(f"\nОшибка исполнителя: {e}")
                await asyncio.sleep(1)
    
    async def interactive_loop():
        nonlocal current_workers, current_handler, executor, running
        
        # Запускаем исполнителя в фоне
        exec_task = asyncio.create_task(run_executor())
        
        try:
            while running:
                cmd = await asyncio.get_event_loop().run_in_executor(None, input, "\n> ")
                cmd = cmd.strip().lower()
                
                if not cmd:
                    continue
                
                if cmd == "stop":
                    print("Остановка обработки...")
                    running = False
                    break
                
                elif cmd == "status":
                    if executor:
                        print(f"\nСтатус:")
                        print(f"  В очереди: {executor.queue_size}")
                        print(f"  Обработано: {executor.stats['completed']}")
                        print(f"  Ошибок: {executor.stats['failed']}")
                        print(f"  Всего отправлено: {executor.stats['submitted']}")
                    else:
                        print("Исполнитель не запущен")
                
                elif cmd.startswith("workers"):
                    parts = cmd.split()
                    if len(parts) == 2 and parts[1].isdigit():
                        new_workers = int(parts[1])
                        if new_workers >= 1:
                            current_workers = new_workers
                            print(f"Количество воркеров изменено на {current_workers}. Перезапуск исполнителя...")
                            running = False
                            await asyncio.sleep(1)
                            running = True
                            exec_task = asyncio.create_task(run_executor())
                        else:
                            print("Количество воркеров должно быть >= 1")
                    else:
                        print("Использование: workers <число>")
                
                elif cmd.startswith("handler"):
                    parts = cmd.split()
                    if len(parts) == 2 and parts[1] in handlers_map:
                        current_handler = handlers_map[parts[1]]()
                        print(f"Обработчик изменен на {type(current_handler).__name__}. Перезапуск исполнителя...")
                        running = False
                        await asyncio.sleep(1)
                        running = True
                        exec_task = asyncio.create_task(run_executor())
                    else:
                        print(f"Доступные обработчики: {', '.join(handlers_map.keys())}")
                
                elif cmd.startswith("add-test"):
                    parts = cmd.split()
                    n = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 5
                    n = min(n, 100)
                    
                    for i in range(n):
                        task = Task(
                            id=f"test_{datetime.now().strftime('%H%M%S')}_{i}",
                            title=f"Тестовая задача {i}",
                            author="interactive",
                            content=f"Автоматически созданная задача {i}",
                            priority=(i % 5) + 1
                        )
                        if executor:
                            await executor.submit(task)
                    print(f"Добавлено {n} тестовых задач")
                
                elif cmd.startswith("add"):
                    parts = cmd.split()
                    if len(parts) >= 3:
                        task_id = parts[1]
                        title = " ".join(parts[2:5]) if len(parts) > 3 else parts[2]
                        priority = int(parts[-1]) if parts[-1].isdigit() else 3
                        
                        task = Task(
                            id=task_id,
                            title=title[:50],
                            author="interactive",
                            content="Интерактивная задача",
                            priority=priority
                        )
                        if executor:
                            await executor.submit(task)
                            print(f"Задача '{task_id}' добавлена в очередь")
                        else:
                            print("Исполнитель не готов")
                    else:
                        print("Использование: add <id> <title> [priority]")
                
                else:
                    print("Неизвестная команда. Доступны: add, add-test, status, workers, handler, stop")
        
        except KeyboardInterrupt:
            print("\n\nПрерывание...")
            running = False
        finally:
            if executor:
                await asyncio.sleep(2)
            exec_task.cancel()

    asyncio.run(interactive_loop())
    print("\nИнтерактивный режим завершен")


def main_loop() -> None:
    """Главный цикл программы"""
    print("Добро пожаловать в систему управления задачами!")
    print("Введите 'instruct' для списка команд или 'exit' для выхода.\n")
    
    if len(sys.argv) > 1:
        try:
            cli()
        except SystemExit:
            pass

    while True:
        try:
            command_line = input("Введите команду: ").strip()
            
            if not command_line:
                continue
            
            if command_line.lower() == "exit":
                print("Выход из программы...")
                break

            parts = command_line.split()
            cmd = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []

            temp_cli = Typer(no_args_is_help=True, add_completion=False)
            
            # копируем команды в временный CLI
            temp_cli.command("instruct")(display_instructions)
            temp_cli.command("sources")(list_sources)
            temp_cli.command("read")(read_tasks)
            temp_cli.command("start")(start_task)
            temp_cli.command("review")(review_task)
            temp_cli.command("complete")(complete_task)
            temp_cli.command("archive")(archive_task)
            temp_cli.command("info")(task_info)
            temp_cli.command("list")(list_all_tasks)
            temp_cli.command("create")(create_task_interactive)
            temp_cli.command("queue-init")(initialize_queue)
            temp_cli.command("queue-demo")(demonstrate_queue)
            temp_cli.command("queue-filter")(filter_queue)
            temp_cli.command("queue-process")(queue_process_demo)
            temp_cli.command("async-demo")(async_demo)
            temp_cli.command("async-interactive")(async_interactive)
            

            try:
                sys.argv = ["temp_cli"] + [cmd] + args
                temp_cli()
            except SystemExit:
                pass
            except Exception as e:
                print(f"Ошибка: {e}")
                
        except KeyboardInterrupt:
            print("\nВыход...")
            break
        except EOFError:
            print("\nВыход...")
            break
        except Exception as e:
            print(f"Неожиданная ошибка: {e}")