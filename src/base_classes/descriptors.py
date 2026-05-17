from typing import Optional, Any, Callable
from src.base_classes.exceptions import TaskStateError, TaskValidationError

class NonEmptyStringDescriptor:
    """
    Data дескриптор для валидации непустых строк заданного размера.
    """
    def __init__(self, name: str, min_length: int = 1, max_length: int = 200):
        """
        Инициализация дескриптора.

        :param name: Название свойства
        :param min_length: Минимальная длина строки
        :param max_length: Максимальная длина строки
        """
        self.name = f"_{name}"
        self.min_length = min_length
        self.max_length = max_length
    
    def __get__(self, instance: Optional[object], owner: type) -> Any:
        if instance is None:
            return self
        return getattr(instance, self.name, None)
    
    def __set__(self, instance: object, value: str) -> None:
        if not isinstance(value, str):
            raise TaskValidationError(
                f"{self.name[1:]} должен быть строкой, получен {type(value).__name__}"
            )
        
        stripped = value.strip()
        if len(stripped) < self.min_length:
            raise TaskValidationError(
                f"{self.name[1:]} не может быть пустым или короче {self.min_length} символов"
            )
        
        if len(stripped) > self.max_length:
            raise TaskValidationError(
                f"{self.name[1:]} не может быть длиннее {self.max_length} символов"
            )
        
        setattr(instance, self.name, stripped)

class PositiveIntDescriptor:
    """
    Data дескриптор для валидации положительных целых чисел в заданном диапазоне.
    """
    def __init__(self, min_value: int = 1, max_value: int = 10):
        """
        Инициализация дескриптора.

        :param min_value: Минимальное значение целого числа
        :param max_value: Максимальное значение целого числа
        """
        self.min_value = min_value
        self.max_value = max_value
        self.name = None
    
    def __set_name__(self, owner: type, name: str) -> None:
        self.name = f"_{name}"
    
    def __get__(self, instance: Optional[object], owner: type) -> Any:
        if instance is None:
            return self
        return getattr(instance, self.name, None)
    
    def __set__(self, instance: object, value: int) -> None:
        if not isinstance(value, int):
            raise TaskValidationError(
                f"{self.name[1:]} должен быть целым числом, получен {type(value).__name__}"
            )
        
        if value < self.min_value:
            raise TaskValidationError(
                f"{self.name[1:]} не может быть меньше {self.min_value}"
            )
        
        if value > self.max_value:
            raise TaskValidationError(
                f"{self.name[1:]} не может быть больше {self.max_value}"
            )
        
        setattr(instance, self.name, value)
    
    def __delete__(self, instance: object) -> None:
        raise TaskStateError(f"Нельзя удалить атрибут {self.name[1:]}")

class ComputedProperty:
    """
    Non-data descriptor для вычисляемых свойств.
    """
    def __init__(self, getter_func: Callable):
        """
        Инициализация дескриптора.

        :param getter_func: Функция для вычисления значения свойства
        """
        self.getter_func = getter_func

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return self.getter_func(obj)