from collections.abc import Iterable
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any
from src.base_classes.task import Task
from src.sources.registry import register_source

def parse_json_file(line: str, path: str, line_no: int) -> dict[str, Any]:
    try:
        return json.loads(line)
    except json.JSONDecodeError as e:
        raise ValueError(f"Ошибка в JSON файле {path}: {line_no}: {e}") from e
#from делает исходную ошибку __cause__ для кастомной ошибки

@dataclass(frozen=True)
class JsonlSource:
    '''
    Класс источников задач в виде файлов формата JSONL
    '''
    path: Path
    name: str = "jsonl-file"

    def get_tasks(self) -> Iterable[Task]:
        '''
        Читает JSONL файл и возвращает все задачи, найденные в нем

        :return: Итератор по всем найденным в файле задачам
        '''
        with self.path.open("r", encoding="utf-8") as file:
            for line_no, line in enumerate(file, start=1):
                line = line.strip()
                if not line:
                    continue

                task = parse_json_file(line, str(self.path), line_no)
                task_id = str(task.get("id", f"{self.path.name}:{line_no}"))
                task_title = task.get("title", "")
                task_author = task.get("author", "")
                task_content = task.get("content", "")
                task_priority = task.get("priority", None)
                if task_priority:
                    yield Task(id=task_id, title=task_title, author=task_author, content=task_content, priority=task_priority)
                else:
                    yield Task(id=task_id, title=task_title, author=task_author, content=task_content)

@register_source("jsonl-file")
def create_json_source(path: Path) -> JsonlSource:
    '''
    Создает источник на основе заданного JSONL файла и регестрирует его

    :param path: Путь к JSONL файлу
    :return: Источник задач
    '''
    return JsonlSource(path=path)