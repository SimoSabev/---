"""Анализ на натоварването на екипа и напредъка по проектите."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

from .manager import TaskManager
from .models import (
    PRIORITY_CRITICAL, PRIORITY_LABELS, STATUS_DONE, STATUS_IN_PROGRESS, STATUS_PENDING,
    Member, Project, Task,
)
from .sorting import merge_sort, quick_sort

# Прагове на натоварване (отношение часове/капацитет)
LEVEL_LOW = 0.5
LEVEL_HIGH = 0.9


def load_level(utilization: float) -> str:
    if utilization > 1.0:
        return "Претоварен"
    if utilization >= LEVEL_HIGH:
        return "Натоварен"
    if utilization >= LEVEL_LOW:
        return "Оптимален"
    return "Свободен"


def progress_bar(ratio: float, width: int = 20) -> str:
    """Текстова лента: 50% -> ██████████░░░░░░░░░░ ; над 100% се отбелязва с '!'."""
    filled = max(0, min(width, round(ratio * width)))
    bar = "█" * filled + "░" * (width - filled)
    return bar + ("!" if ratio > 1.0 else " ")


@dataclass
class MemberLoad:
    member: Member
    active_count: int = 0
    active_hours: float = 0.0
    done_count: int = 0
    done_hours: float = 0.0
    overdue_count: int = 0
    critical_count: int = 0

    @property
    def utilization(self) -> float:
        return self.active_hours / self.member.capacity if self.member.capacity else 0.0

    @property
    def free_hours(self) -> float:
        return self.member.capacity - self.active_hours

    @property
    def level(self) -> str:
        return load_level(self.utilization)


@dataclass
class ProjectProgress:
    project: Project
    total: int = 0
    done: int = 0
    in_progress: int = 0
    pending: int = 0
    hours_total: float = 0.0
    hours_done: float = 0.0
    overdue: int = 0
    days_left: Optional[int] = None

    @property
    def percent(self) -> float:
        """Напредък по часове (по-точен от брой задачи)."""
        return self.hours_done / self.hours_total if self.hours_total else 0.0

    @property
    def risk(self) -> str:
        if self.total == 0:
            return "Няма задачи"
        if self.done == self.total:
            return "Завършен"
        if self.days_left is not None and self.days_left < 0:
            return "Просрочен"
        if self.overdue or (self.days_left is not None and self.days_left <= 7
                            and self.percent < 0.7):
            return "Риск"
        return "В срок"


@dataclass
class TeamSummary:
    member_count: int = 0
    total_capacity: float = 0.0
    active_hours: float = 0.0
    pending_hours: float = 0.0
    pending_count: int = 0
    active_count: int = 0
    done_count: int = 0
    overdue_count: int = 0
    avg_utilization: float = 0.0
    min_utilization: float = 0.0
    max_utilization: float = 0.0
    overloaded: List[str] = field(default_factory=list)
    idle: List[str] = field(default_factory=list)

    @property
    def team_utilization(self) -> float:
        return self.active_hours / self.total_capacity if self.total_capacity else 0.0

    @property
    def weeks_to_clear(self) -> float:
        """Колко седмици са нужни на целия екип за всички незавършени задачи."""
        if not self.total_capacity:
            return float("inf")
        return (self.active_hours + self.pending_hours) / self.total_capacity

    @property
    def imbalance(self) -> float:
        """Разлика между най-натоварения и най-малко натоварения (в процентни пунктове)."""
        return self.max_utilization - self.min_utilization


# ---------------------------------------------------------------------------
def member_loads(manager: TaskManager, today: Optional[date] = None) -> List[MemberLoad]:
    """Натоварване за всеки член, сортирано низходящо по натоварване (Merge Sort)."""
    today = today or date.today()
    by_member = {m.id: MemberLoad(m) for m in manager.members}
    for task in manager.tasks:
        load = by_member.get(task.assignee_id)
        if load is None:
            continue
        if task.status == STATUS_IN_PROGRESS:
            load.active_count += 1
            load.active_hours += task.estimate_hours
            if task.is_overdue(today):
                load.overdue_count += 1
            if task.priority == PRIORITY_CRITICAL:
                load.critical_count += 1
        elif task.status == STATUS_DONE:
            load.done_count += 1
            load.done_hours += task.estimate_hours
    return merge_sort(list(by_member.values()),
                      key=lambda x: (x.utilization, x.active_hours), reverse=True)


def team_summary(manager: TaskManager, loads: Optional[List[MemberLoad]] = None,
                 today: Optional[date] = None) -> TeamSummary:
    today = today or date.today()
    loads = loads if loads is not None else member_loads(manager, today)
    summary = TeamSummary(member_count=len(loads))
    for task in manager.tasks:
        if task.status == STATUS_PENDING:
            summary.pending_count += 1
            summary.pending_hours += task.estimate_hours
        elif task.status == STATUS_IN_PROGRESS:
            summary.active_count += 1
        else:
            summary.done_count += 1
        if task.is_overdue(today):
            summary.overdue_count += 1
    if loads:
        utils = [x.utilization for x in loads]
        summary.total_capacity = sum(x.member.capacity for x in loads)
        summary.active_hours = sum(x.active_hours for x in loads)
        summary.avg_utilization = sum(utils) / len(utils)
        summary.min_utilization = min(utils)
        summary.max_utilization = max(utils)
        summary.overloaded = [x.member.name for x in loads if x.utilization > 1.0]
        summary.idle = [x.member.name for x in loads if x.utilization < LEVEL_LOW]
    return summary


def project_progress(manager: TaskManager, today: Optional[date] = None) -> List[ProjectProgress]:
    today = today or date.today()
    by_project = {p.id: ProjectProgress(p) for p in manager.projects}
    for task in manager.tasks:
        progress = by_project.get(task.project_id)
        if progress is None:
            continue
        progress.total += 1
        progress.hours_total += task.estimate_hours
        if task.status == STATUS_DONE:
            progress.done += 1
            progress.hours_done += task.estimate_hours
        elif task.status == STATUS_IN_PROGRESS:
            progress.in_progress += 1
        else:
            progress.pending += 1
        if task.is_overdue(today):
            progress.overdue += 1
    for progress in by_project.values():
        if progress.project.deadline:
            progress.days_left = (date.fromisoformat(progress.project.deadline) - today).days
    return list(by_project.values())


def recommendations(manager: TaskManager, loads: List[MemberLoad],
                    today: Optional[date] = None) -> List[str]:
    """Конкретни препоръки за балансиране на натоварването."""
    today = today or date.today()
    tips: List[str] = []
    # Текущо натоварване в часове – обновява се при всяко предложено преместване,
    # за да не се препоръчват две задачи към един и същ човек над капацитета му.
    hours = {x.member.id: x.active_hours for x in loads}

    for load in loads:
        if load.utilization <= 1.0:
            continue
        member = load.member
        # Задачите на претоварения – първо най-маловажните (Quick Sort по приоритет).
        movable = quick_sort(manager.active_tasks_of(member.id),
                             key=lambda t: (t.priority, -t.estimate_hours, t.id))
        for task in movable:
            if hours[member.id] <= member.capacity:
                break
            target = _best_receiver(manager, task, member.id, hours)
            if target is None:
                continue
            hours[member.id] -= task.estimate_hours
            hours[target.id] += task.estimate_hours
            tips.append(
                f"Преместете задача #{task.id} „{task.title}“ ({task.estimate_hours:g} ч) "
                f"от {member.name} към {target.name} "
                f"(след това: {hours[target.id]:g}/{target.capacity:g} ч)."
            )
        if hours[member.id] > member.capacity:
            tips.append(
                f"{member.name} остава претоварен/а с {hours[member.id] - member.capacity:g} ч – "
                f"върнете задача в опашката или удължете срок."
            )

    pending = manager.pending_tasks()
    critical_behind, lower_seen = [], False
    for task in pending:
        if task.priority == PRIORITY_CRITICAL and lower_seen:
            critical_behind.append(task)
        lower_seen = lower_seen or task.priority < PRIORITY_CRITICAL
    if critical_behind:
        tips.append(f"В опашката има {len(critical_behind)} критични задачи зад по-маловажни – "
                    f"използвайте „Пренареди опашката по приоритет“.")

    overdue = manager.filter_tasks(overdue_only=True, today=today)
    if overdue:
        ids = ", ".join(f"#{t.id}" for t in overdue[:8])
        tips.append(f"Просрочени задачи ({len(overdue)}): {ids} – приоритизирайте ги.")

    free = [x for x in loads if x.utilization < LEVEL_LOW]
    if free and pending:
        names = ", ".join(x.member.name for x in free)
        tips.append(f"Свободен капацитет имат: {names} – използвайте „Автоматично разпределение“.")

    summary = team_summary(manager, loads, today)
    if summary.weeks_to_clear > 2 and summary.weeks_to_clear != float("inf"):
        tips.append(f"Всички незавършени задачи изискват ~{summary.weeks_to_clear:.1f} седмици "
                    f"работа на целия екип – обмислете разширяване на екипа или намаляване на обхвата.")

    if not tips:
        tips.append("Натоварването е балансирано – няма нужда от действия.")
    return tips


def _best_receiver(manager: TaskManager, task: Task, exclude_id: int,
                   hours: dict) -> Optional[Member]:
    """Най-малко натовареният член (със същата роля, ако задачата изисква),
    който може да поеме задачата, без да надхвърли капацитета си."""
    best, best_ratio = None, None
    for member in manager.members:
        if member.id == exclude_id:
            continue
        if task.required_role and member.role != task.required_role:
            continue
        new_hours = hours.get(member.id, 0.0) + task.estimate_hours
        if new_hours > member.capacity:
            continue
        ratio = new_hours / member.capacity
        if best_ratio is None or ratio < best_ratio:
            best, best_ratio = member, ratio
    return best


# ---------------------------------------------------------------------------
def build_text_report(manager: TaskManager, today: Optional[date] = None) -> str:
    """Пълен текстов отчет за натоварването (за експорт във файл)."""
    today = today or date.today()
    loads = member_loads(manager, today)
    summary = team_summary(manager, loads, today)
    lines = [
        "ОТЧЕТ ЗА НАТОВАРВАНЕТО НА AI ЕКИПА",
        f"Дата: {today.strftime('%d.%m.%Y')}",
        "=" * 72,
        "",
        "ОБОБЩЕНИЕ",
        f"  Членове на екипа:          {summary.member_count}",
        f"  Общ капацитет:             {summary.total_capacity:g} ч/седмица",
        f"  Задачи в процес:           {summary.active_count} ({summary.active_hours:g} ч)",
        f"  Чакащи задачи (опашка):    {summary.pending_count} ({summary.pending_hours:g} ч)",
        f"  Приключени задачи (стек):  {summary.done_count}",
        f"  Просрочени задачи:         {summary.overdue_count}",
        f"  Натоварване на екипа:      {summary.team_utilization:.0%}",
        f"  Средно натоварване:        {summary.avg_utilization:.0%}",
        f"  Дисбаланс (макс − мин):    {summary.imbalance:.0%}",
        f"  Седмици до изчистване:     {summary.weeks_to_clear:.1f}",
        "",
        "НАТОВАРВАНЕ ПО ИЗПЪЛНИТЕЛИ",
    ]
    for x in loads:
        lines.append(f"  {x.member.name:<24} {progress_bar(x.utilization)} {x.utilization:>5.0%}  "
                     f"{x.active_hours:g}/{x.member.capacity:g} ч  [{x.level}]")
        lines.append(f"  {'':<24} роля: {x.member.role}; в процес: {x.active_count}; "
                     f"приключени: {x.done_count}; просрочени: {x.overdue_count}")
    lines += ["", "НАПРЕДЪК ПО ПРОЕКТИ"]
    for p in project_progress(manager, today):
        deadline = (date.fromisoformat(p.project.deadline).strftime("%d.%m.%Y")
                    if p.project.deadline else "без срок")
        lines.append(f"  {p.project.name:<34} {progress_bar(p.percent)} {p.percent:>5.0%}  "
                     f"[{p.risk}]")
        lines.append(f"  {'':<34} задачи: {p.done}/{p.total} приключени; срок: {deadline}")
    lines += ["", "ПРЕПОРЪКИ"]
    lines += [f"  • {tip}" for tip in recommendations(manager, loads, today)]
    lines += ["", "ПРИОРИТЕТИ: " + ", ".join(f"{k} = {v}" for k, v in PRIORITY_LABELS.items())]
    return "\n".join(lines) + "\n"
