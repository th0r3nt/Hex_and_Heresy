"""
Централизованная конфигурация логирования.
Инкапсулирует настройку форматов и обработчиков (handlers).
Остальные модули системы просто импортируют готовый `main_logger`.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def _setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Фабрика настройки логгера.
    Создает логгер с выводом в консоль (stdout) и в ротируемый файл.
    """
    logger = logging.getLogger(name)

    # Защита от дублирования обработчиков при повторных импортах
    if logger.hasHandlers():
        return logger

    logger.setLevel(level)
    logger.propagate = (
        False  # Отключаем всплытие логов к корневому логгеру во избежание дублей
    )

    # Единый формат для всех выводов
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)-8s [%(name)s:%(module)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. Вывод в консоль (stdout для Electron/FastAPI)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    logger.addHandler(console_handler)

    # 2. Вывод в файл (с ротацией: максимум 5 МБ на файл, храним 3 бэкапа)
    # Файлы логов полезны для отладки локального десктопного приложения
    log_dir = Path("logs")
    try:
        log_dir.mkdir(exist_ok=True)
        file_handler = RotatingFileHandler(
            filename=log_dir / "hex_and_heresy.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)  # В файл всегда пишем максимум информации
        logger.addHandler(file_handler)
    except OSError as e:
        # Если нет прав на запись в директорию, тихо падаем до консольного логгера
        logger.warning(f"Не удалось инициализировать файловый логгер: {e}")

    return logger


# Экспортируемый синглтон логгера для всего приложения
main_logger = _setup_logger("hex_and_heresy")
