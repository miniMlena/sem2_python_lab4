from datetime import datetime
from typing import Dict, Optional
from src.base_classes.descriptors import PositiveIntDescriptor, NonEmptyStringDescriptor, ComputedProperty
from src.base_classes.enums import TaskStatus, TaskPriority, allowed_transitions
from src.base_classes.exceptions import TaskStateError, TaskValidationError

class Task:
    """
    Класс для представления задачи.
    """
    # дескрипторы для валидации
    id = NonEmptyStringDescriptor("id", min_length=1, max_length=50)
    title = NonEmptyStringDescriptor("title", min_length=3, max_length=100)
    author = NonEmptyStringDescriptor("author", min_length=2, max_length=50)
    content = NonEmptyStringDescriptor("content", min_length=1, max_length=1000)
    priority = PositiveIntDescriptor(min_value=1, max_value=5)
    
    def __init__(
        self,
        id: str,
        title: str,
        author: str,
        content: str,
        priority: TaskPriority | int = TaskPriority.MEDIUM,
        status: TaskStatus = TaskStatus.PENDING
    ):
        """Инициализация задачи с валидацией."""
        # внутреннее состояние
        self._status = TaskStatus.PENDING
        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None
        
        # Установка значений пройдет через дескрипторы
        self.id = id
        self.title = title
        self.author = author
        self.content = content
        
        if isinstance(priority, TaskPriority):
            self.priority = priority.value
        elif isinstance(priority, int):
            self.priority = priority
        else:
            raise TaskValidationError(
                f"priority должен быть TaskPriority или int, получен {type(priority).__name__}"
            )
        
        self._created_at = datetime.now() #благодаря property нельзя будет изменить
        self.status = status # пройдет через property

    # СВОЙСТВА

    @property
    def created_at(self) -> datetime:
        """Время создания задачи (только для чтения)"""
        return self._created_at

    @property
    def status(self) -> TaskStatus:
        """Текущий статус задачи"""
        return self._status
    
    @status.setter
    def status(self, value: TaskStatus) -> None:
        """
        Установка статуса с валидацией переходов, защищает инварианты состояния задачи.

        :param value: Новый статус задачи
        """
        if not isinstance(value, TaskStatus):
            raise TaskValidationError(
                f"status должен быть TaskStatus, получен {type(value).__name__}"
            )
        
        old_status = self._status
        
        # валидация переходов статусов
        if old_status != value:

            if value not in allowed_transitions.get(old_status, set()):
                raise TaskStateError(
                    f"Недопустимый переход из {old_status.value} в {value.value}"
                )

            # обновление временных меток
            if value == TaskStatus.IN_PROGRESS and self._started_at is None:
                self._started_at = datetime.now()
            
            if value == TaskStatus.DONE and self._completed_at is None:
                self._completed_at = datetime.now()
            
            self._status = value
    
    @property
    def priority_label(self) -> TaskPriority:
        """Приоритет в виде названия (только для чтения)"""
        return TaskPriority(self.priority)

    @property
    def started_at(self) -> Optional[datetime]:
        """Время начала выполнения задачи (только для чтения)"""
        return self._started_at
    
    @property
    def completed_at(self) -> Optional[datetime]:
        """Время завершения (только для чтения)"""
        return self._completed_at
    
    @ComputedProperty
    def work_duration(self) -> Optional[float]:
        """Общее время выполнения задачи в секундах."""
        if self.completed_at is not None:
            delta = self.completed_at - self.started_at
            return delta.total_seconds()

        return None

    @ComputedProperty
    def age_seconds(self) -> float:
        """Возраст задачи в секундах с момента создания."""
        return (datetime.now() - self.created_at).total_seconds()
    
    # ПУБЛИЧНЫЕ МЕТОДЫ
    
    def start(self) -> None:
        """Начать выполнение задачи"""
        if self._status not in {TaskStatus.PENDING, TaskStatus.REVIEW}:
            raise TaskStateError(
                f"Нельзя начать задачу в статусе '{self._status.value}'. "
                "Доступно для PENDING или REVIEW"
            )
        self.status = TaskStatus.IN_PROGRESS
    
    def complete(self) -> None:
        """Завершить задачу"""
        if self._status not in (TaskStatus.IN_PROGRESS, TaskStatus.REVIEW):
            raise TaskStateError(
                f"Нельзя завершить задачу в статусе '{self._status.value}'. "
                "Требуется статус IN_PROGRESS или REVIEW"
            )
        self.status = TaskStatus.DONE
    
    def review(self) -> None:
        """Отправить на проверку"""
        if self._status != TaskStatus.IN_PROGRESS:
            raise TaskStateError(
                f"Нельзя отправить на проверку задачу в статусе '{self._status.value}'. "
                "Требуется статус IN_PROGRESS"
            )
        self.status = TaskStatus.REVIEW
    
    def archive(self) -> None:
        """Архивировать задачу"""
        if self._status != TaskStatus.DONE:
            raise TaskStateError(
                f"Нельзя архивировать задачу в статусе '{self._status.value}'. "
                "Требуется статус DONE"
            )
        self.status = TaskStatus.ARCHIVED
    
    def to_dict(self) -> Dict:
        """Экспорт задачи в словарь"""
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "content": self.content,
            "priority": self.priority,
            "priority_label": str(self.priority_label),
            "status": str(self.status),
            "created_at": self.created_at.isoformat(sep=' ', timespec='seconds'),
            "started_at": self.started_at.isoformat(sep=' ', timespec='seconds') if self.started_at else None,
            "completed_at": self.completed_at.isoformat(sep=' ', timespec='seconds') if self.completed_at else None,
            "age_seconds": self.age_seconds,
            "work_duration": self.work_duration
        }
    
    def __str__(self) -> str:
        return f"Task(id={self.id}, title='{self.title}', author={self.author}, content='{self.content}', priority={self.priority})"
    
    def __repr__(self) -> str:
        return (
            f"Task(id={self.id!r}, title={self.title!r}, author={self.author!r}, "
            f"priority={self.priority}, status={self.status})"
        )