class TaskError(Exception):
    """Базовое исключение для ошибок задачи"""
    pass

class TaskValidationError(TaskError):
    """Ошибка валидации атрибутов задачи"""
    pass

class TaskStateError(TaskError):
    """Ошибка состояния задачи"""
    pass