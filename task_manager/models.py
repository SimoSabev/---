"""Модели на данните: проект, член на екипа (изпълнител) и задача."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import date
from typing import Optional

# --- Приоритети -------------------------------------------------------------
PRIORITY_LOW = 1
PRIORITY_MEDIUM = 2
PRIORITY_HIGH = 3
PRIORITY_CRITICAL = 4

PRIORITY_LABELS = {
    PRIORITY_LOW: "Нисък",
    PRIORITY_MEDIUM: "Среден",
    PRIORITY_HIGH: "Висок",
    PRIORITY_CRITICAL: "Критичен",
}

# --- Статуси на задача -------------------------------------------------------
STATUS_PENDING = "pending"          # чака в опашката (queue)
STATUS_IN_PROGRESS = "in_progress"  # възложена на изпълнител
STATUS_DONE = "done"                # приключена (в стека)

STATUS_LABELS = {
    STATUS_PENDING: "Чакаща",
    STATUS_IN_PROGRESS: "В процес",
    STATUS_DONE: "Приключена",
}

# --- Роли в AI екипа ---------------------------------------------------------
ROLES = (
    "ML инженер",
    "Data инженер",
    "MLOps инженер",
    "AI изследовател",
    "Backend разработчик",
    "QA / оценка на модели",
)

# Използва се като "безкрайно далечен" срок при сортиране на задачи без срок.
NO_DEADLINE_KEY = "9999-12-31"


def _from_dict(cls, data: dict):
    """Създава dataclass обект, като игнорира непознати ключове (за съвместимост)."""
    allowed = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in allowed})


@dataclass
class Project:
    id: int
    name: str
    description: str = ""
    deadline: Optional[str] = None  # ISO формат ГГГГ-ММ-ДД

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        return _from_dict(cls, data)


@dataclass
class Member:
    """Изпълнител – член на AI екипа."""

    id: int
    name: str
    role: str
    capacity: float = 40.0  # капацитет в часове на седмица

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Member":
        return _from_dict(cls, data)


@dataclass
class Task:
    id: int
    title: str
    project_id: int
    priority: int = PRIORITY_MEDIUM
    estimate_hours: float = 1.0
    deadline: Optional[str] = None
    description: str = ""
    required_role: Optional[str] = None
    status: str = STATUS_PENDING
    assignee_id: Optional[int] = None
    created_on: str = ""
    completed_on: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.created_on:
            self.created_on = date.today().isoformat()

    # --- помощни методи ---
    @property
    def deadline_key(self) -> str:
        """Ключ за сортиране по срок; задачи без срок отиват най-накрая."""
        return self.deadline or NO_DEADLINE_KEY

    @property
    def priority_label(self) -> str:
        return PRIORITY_LABELS.get(self.priority, str(self.priority))

    @property
    def status_label(self) -> str:
        return STATUS_LABELS.get(self.status, self.status)

    def is_overdue(self, today: Optional[date] = None) -> bool:
        """Незавършена задача с изтекъл срок."""
        if self.status == STATUS_DONE or not self.deadline:
            return False
        today = today or date.today()
        return date.fromisoformat(self.deadline) < today

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return _from_dict(cls, data)
