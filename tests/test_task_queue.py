import pytest
from collections.abc import Iterable
from tests.fixtures import MockTaskManager, sample_tasks, task_manager, task_queue
from src.base_classes.enums import TaskStatus
from src.base_classes.task_queue import TaskQueue


def test_queue_initialization(task_queue):
    """Тест: корректной инициализации очереди"""
    assert task_queue._manager is not None
    assert task_queue._cache == []
    assert task_queue._fully_consumed is False
    assert task_queue._task_iterator is None


def test_queue_multiple_iterations_work(task_queue, sample_tasks):
    """Тест поддержки многократной итерации"""
    first_iteration = [task.id for task in task_queue]
    second_iteration = [task.id for task in task_queue]
    
    assert first_iteration == second_iteration
    assert task_queue._fully_consumed is True


def test_queue_reset(task_queue, sample_tasks):
    """Тест сброса очереди"""
    first_pass = list(task_queue)
    assert task_queue._fully_consumed is True
    assert len(task_queue._cache) == len(sample_tasks)
    
    task_queue.reset()
    
    assert task_queue._cache == []
    assert task_queue._fully_consumed is False
    assert task_queue._task_iterator is None
    
    second_pass = list(task_queue)
    assert len(second_pass) == len(first_pass)


# тесты для фильтров

def test_filter_by_tasks_attrs(task_queue):
    """Тест фильтрации по приоритетам, автору и названию"""
    high_priority_tasks = list(task_queue.filter_by_priority(4, 5))
    
    assert len(high_priority_tasks) == 2
    for task in high_priority_tasks:
        assert task.priority in (4, 5)

    milenas_tasks = list(task_queue.filter_by_author("милена"))  # заодно проверяем регистронезависимость
    
    assert len(milenas_tasks) == 2
    for task in milenas_tasks:
        assert task.author.lower() == "милена"

    contains_critical = list(task_queue.filter_by_title_contains("критическая"))
    
    assert len(contains_critical) == 1
    assert contains_critical[0].id == "4"
    assert "критическая" in contains_critical[0].title.lower()


def test_filter_is_lazy(task_queue):
    """Тест, что фильтр ленивый (выполняет итерацию только по запросу)"""
    filtered = task_queue.filter_by_status(TaskStatus.PENDING)
    
    assert len(task_queue._cache) == 0
    assert isinstance(filtered, Iterable)
    
    list(filtered)
    assert len(task_queue._cache) > 0


def test_status_filter(task_queue):
    """Тесты фильтрации по статусу"""
    pending = list(task_queue.pending())
    
    assert len(pending) == 2
    for task in pending:
        assert task.status == TaskStatus.PENDING

    in_progress = list(task_queue.in_progress())
    
    assert len(in_progress) == 1
    assert in_progress[0].status == TaskStatus.IN_PROGRESS
    assert in_progress[0].id == "2"

    done = list(task_queue.done())
    
    assert len(done) == 1
    assert done[0].status == TaskStatus.DONE
    assert done[0].id == "3"

def test_high_priority_filter(task_queue):
    """Тест фильтрации с высокм приоритетом"""
    high_priority = list(task_queue.high_priority())

    assert len(high_priority) == 2
    for task in high_priority:
        assert task.priority >= 4


# тесты для потоковой обработки

def test_process_default_behavior(task_queue, sample_tasks):
    """Тест успешной потоковой обработки без функции трансформации"""
    processed = list(task_queue.process())
    
    assert len(processed) == len(sample_tasks)
    for i, task in enumerate(processed):
        assert task is sample_tasks[i]

def test_process_with_transformation(task_queue):
    """Тест успешной потоковой обработки с функцией трансформации"""
    result = list(task_queue.process(lambda t: (t.id, t.title)))
    
    assert len(result) == 5
    assert result[0] == ("1", "Простая задача")
    assert result[1] == ("2", "Срочная задача")

def test_process_is_lazy(task_queue):
    """Тест, что при потоковой обработке задачи обрабатываются только по запросу (лениво)"""
    processed = task_queue.process(lambda t: t.id)
    
    assert len(task_queue._cache) == 0

    first_id = next(iter(processed))
    
    assert len(task_queue._cache) == 1
    assert first_id == "1"


# тесты краевых случаев

def test_empty_queue():
    """Тест очереди без задач"""
    empty_manager = MockTaskManager([])
    empty_queue = TaskQueue(empty_manager)
    
    assert list(empty_queue) == []
    assert empty_queue._fully_consumed is True
    
    assert list(empty_queue) == []


def test_iterator_on_already_consumed_queue(task_queue, sample_tasks):
    """Тест повторной итерации"""
    list(task_queue)
    assert task_queue._fully_consumed is True
    
    second_pass = list(task_queue)
    assert len(second_pass) == len(sample_tasks)