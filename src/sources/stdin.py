import sys
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TextIO, Tuple
from src.base_classes.task import Task
from src.sources.registry import register_source

def extract_tasks(lines: list[str], line_no: int) -> Tuple[str | None]:
    '''
    Выделает из строки текста 4 параметра задачи

    :param lines: Строка с текстом задачи
    :param line_no: Номер строки в вводе
    :return: Параметры задчи
    '''
    try:
        if len(lines) >= 5:
            return lines[0], lines[1], lines[2], lines[3], lines[4]
        else:
            return lines[0], lines[1], lines[2], lines[3], None
    except IndexError:
        raise ValueError(
            f"Некорректная строка: {line_no}. Задача должна состоять из хотя бы 4 частей, разделенных символом ':'"
        )

@dataclass(frozen=True)
class StdinLineSource:
    '''
    Класс источников задач в виде строк стандартного ввода
    '''
    stream: TextIO = sys.stdin
    name: str = "stdin"
    stop_sign: str = "stop"

    def get_tasks(self) -> Iterable[Task]:
        '''
        Выделяет задачи из введенных строк

        :return: Итератор по выделенным задачам
        '''
        for line_no, line in enumerate(self.stream, start=1):
            if line.strip().lower() == self.stop_sign.lower():
                break
            lines = line.split(":")
            if not line.strip():
                continue
            id, title, author, content, priority = extract_tasks(lines, line_no)
            yield Task(id=id, title=title, author=author, content=content, priority=int(priority))

@register_source("stdin")
def create_source() -> StdinLineSource:
    '''
    Создает источник из строки стандартного ввода

    :return: Источник задач
    '''
    return StdinLineSource()