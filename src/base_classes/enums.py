from enum import Enum
from typing import Dict

class TaskPriority(Enum):
    """Приоритеты задачи"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5
    
    def __str__(self) -> str:
        names = {1: "Низкий", 2: "Средний", 3: "Высокий", 4: "Срочный", 5: "Критический"}
        return names[self.value]

class TaskStatus(Enum):
    """Статусы выполнения задачи"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    ARCHIVED = "archived"
    
    def __str__(self) -> str:
        return self.value
    
allowed_transitions: Dict = {
    TaskStatus.PENDING: {TaskStatus.IN_PROGRESS},
    TaskStatus.IN_PROGRESS: {TaskStatus.REVIEW, TaskStatus.DONE},
    TaskStatus.REVIEW: {TaskStatus.IN_PROGRESS, TaskStatus.DONE},
    TaskStatus.DONE: {TaskStatus.ARCHIVED},
    TaskStatus.ARCHIVED: set(),
}