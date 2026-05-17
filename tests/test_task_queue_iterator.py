import pytest
from tests.fixtures import sample_tasks, task_manager, task_queue


def test_iterator_raises_stop_iteration_when_exhausted(task_queue, sample_tasks):
    """Тест, что итератор выбрасывает StopIteration после исчерпания"""
    iterator = iter(task_queue)

    for _ in range(len(sample_tasks)):
        next(iterator)

    with pytest.raises(StopIteration):
        next(iterator)

def test_iterator_uses_cache_on_second_iteration(task_queue, sample_tasks):
    """Тестируем, что при повторной итерации данные берутся из кэша"""
    first_pass = list(task_queue)

    cached_tasks = task_queue._cache.copy()

    second_pass = list(task_queue)
    
    assert len(first_pass) == len(second_pass)
    for i, task in enumerate(second_pass):
        assert task.id == first_pass[i].id
        assert task is cached_tasks[i]

def test_multiple_iterators_share_cache(task_queue, sample_tasks):
    """Тест, что несколько итераторов одной и той же очереди разделяют один кэш"""
    iterator1 = iter(task_queue)
    iterator2 = iter(task_queue)

    task1 = next(iterator1)

    task_from_second = next(iterator2)
    
    assert task1.id == task_from_second.id
    assert task1 is task_from_second

def test_iterator_caches_only_consumed_tasks(task_queue):
    """Тест, что итератор кэширует только те задачи, которые были запрошены"""
    iterator = iter(task_queue)

    first_task = next(iterator)
    
    assert len(task_queue._cache) == 1
    assert task_queue._cache[0] is first_task