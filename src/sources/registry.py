from typing import Callable, Type
from src.base_classes.task_source import TaskSource

SourceFactory = Callable[..., TaskSource]

REGISTRY: dict[str, SourceFactory] = {}

def register_source(name: str):
    '''
    Регистрирует источник задач под переданным именем в общем регистраторе
    
    :param name: Имя источника для регистрации
    '''
    def _decorator(class_or_function: Type | Callable):
        REGISTRY[name] = class_or_function
        return class_or_function
    return _decorator