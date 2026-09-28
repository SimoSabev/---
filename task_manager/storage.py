"""Запис и зареждане на данните в JSON файл."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Tuple

from .manager import TaskManager

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "tasks_data.json"


def save(manager: TaskManager, path: Path = DATA_FILE) -> None:
    """Атомарен запис: първо във временен файл, после замяна на стария.

    Така при прекъсване по време на запис старите данни не се губят.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(manager.to_dict(), f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def load(path: Path = DATA_FILE) -> Tuple[TaskManager, str]:
    """Зарежда данните. Връща (мениджър, съобщение).

    Ако файлът липсва – създава демонстрационни данни.
    Ако файлът е повреден – прави резервно копие и започва с демо данни.
    """
    from .demo_data import create_demo_manager

    path = Path(path)
    if not path.exists():
        return create_demo_manager(), "Файл с данни не е намерен – заредени са демонстрационни данни."
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("неочакван формат")
        return TaskManager.from_dict(data), f"Данните са заредени от {path.name}."
    except (OSError, ValueError, TypeError, KeyError) as error:
        backup = path.with_name(f"{path.stem}_повреден_{datetime.now():%Y%m%d_%H%M%S}{path.suffix}")
        try:
            shutil.copy(path, backup)
            where = f" Резервно копие: {backup.name}."
        except OSError:
            where = ""
        return (create_demo_manager(),
                f"Файлът с данни е повреден ({error}).{where} Заредени са демонстрационни данни.")
