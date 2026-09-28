"""Бизнес логика на системата за управление на задачи на AI екип.

Използвани структури от данни:
  * list  – проекти, изпълнители и всички задачи (поддържат се сортирани по ID,
            за да може да се търси по ID с двоично търсене за O(log n));
  * Queue – чакащи задачи (FIFO): нова задача -> в края; поемане -> от началото;
  * Stack – приключени задачи (LIFO): последно приключената е най-отгоре,
            което позволява отмяна (undo) на последното приключване.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, Tuple

from .models import (
    PRIORITY_LABELS, ROLES, STATUS_DONE, STATUS_IN_PROGRESS, STATUS_PENDING,
    Member, Project, Task,
)
from .searching import binary_search, linear_search
from .sorting import merge_sort, quick_sort
from .structures import Queue, Stack

MAX_CAPACITY = 80.0     # часа седмично – горна граница за капацитет
MAX_ESTIMATE = 500.0    # часа – горна граница за оценка на задача


class TaskManagerError(Exception):
    """Грешка, която се показва на потребителя (невалидни данни, липсващ обект...)."""


# Критерии за сортиране на задачи: име -> (описание, ключ)
SORT_CRITERIA = {
    "priority": ("Приоритет (най-важните първи)",
                 lambda t: (-t.priority, t.deadline_key, t.id)),
    "deadline": ("Краен срок (най-спешните първи)",
                 lambda t: (t.deadline_key, -t.priority, t.id)),
    "estimate": ("Оценка в часове (най-кратките първи)",
                 lambda t: (t.estimate_hours, -t.priority, t.id)),
    "title": ("Заглавие (азбучно)",
              lambda t: (t.title.casefold(), t.id)),
}


class TaskManager:
    def __init__(self) -> None:
        self.projects: List[Project] = []
        self.members: List[Member] = []
        self.tasks: List[Task] = []
        self.pending: Queue = Queue()      # чакащи задачи
        self.completed: Stack = Stack()    # приключени задачи
        self.next_ids: Dict[str, int] = {"project": 1, "member": 1, "task": 1}

    # ------------------------------------------------------------------
    # Помощни
    # ------------------------------------------------------------------
    def _new_id(self, kind: str) -> int:
        new_id = self.next_ids[kind]
        self.next_ids[kind] += 1
        return new_id

    @staticmethod
    def _clean_text(value: str, field: str, max_len: int = 120, required: bool = True) -> str:
        value = (value or "").strip()
        if required and not value:
            raise TaskManagerError(f"Полето „{field}“ не може да е празно.")
        if len(value) > max_len:
            raise TaskManagerError(f"Полето „{field}“ е твърде дълго (макс. {max_len} символа).")
        return value

    @staticmethod
    def _validate_date(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError:
            raise TaskManagerError(f"Невалидна дата: {value}") from None

    @staticmethod
    def _validate_priority(priority: int) -> int:
        if priority not in PRIORITY_LABELS:
            raise TaskManagerError("Приоритетът трябва да е между 1 и 4.")
        return priority

    @staticmethod
    def _validate_estimate(hours: float) -> float:
        if not 0 < hours <= MAX_ESTIMATE:
            raise TaskManagerError(f"Оценката трябва да е между 0 и {MAX_ESTIMATE:g} часа.")
        return round(float(hours), 2)

    @staticmethod
    def _find_by_id(items: list, item_id: int, stats: Optional[dict] = None):
        """Двоично търсене по ID (списъците се поддържат сортирани по ID)."""
        index = binary_search(items, item_id, key=lambda x: x.id, stats=stats)
        return items[index] if index >= 0 else None

    # ------------------------------------------------------------------
    # Проекти
    # ------------------------------------------------------------------
    def add_project(self, name: str, description: str = "",
                    deadline: Optional[str] = None) -> Project:
        name = self._clean_text(name, "Име на проект", 60)
        if linear_search(self.projects, lambda p: p.name.casefold() == name.casefold()):
            raise TaskManagerError(f"Вече съществува проект с име „{name}“.")
        project = Project(
            id=self._new_id("project"),
            name=name,
            description=self._clean_text(description, "Описание", 300, required=False),
            deadline=self._validate_date(deadline),
        )
        self.projects.append(project)  # ID-тата растат -> списъкът остава сортиран
        return project

    def get_project(self, project_id: int) -> Project:
        project = self._find_by_id(self.projects, project_id)
        if project is None:
            raise TaskManagerError(f"Няма проект с ID {project_id}.")
        return project

    def delete_project(self, project_id: int) -> int:
        """Изтрива проекта и всичките му задачи. Връща броя изтрити задачи."""
        project = self.get_project(project_id)
        task_ids = {t.id for t in self.tasks_of_project(project.id)}
        for task_id in task_ids:
            self.delete_task(task_id)
        self.projects.remove(project)
        return len(task_ids)

    # ------------------------------------------------------------------
    # Изпълнители (членове на екипа)
    # ------------------------------------------------------------------
    def add_member(self, name: str, role: str, capacity: float = 40.0) -> Member:
        name = self._clean_text(name, "Име", 60)
        if role not in ROLES:
            raise TaskManagerError("Невалидна роля.")
        if not 0 < capacity <= MAX_CAPACITY:
            raise TaskManagerError(f"Капацитетът трябва да е между 0 и {MAX_CAPACITY:g} ч/седмица.")
        if self.find_member_by_name(name) is not None:
            raise TaskManagerError(f"Вече има член на екипа с име „{name}“.")
        member = Member(id=self._new_id("member"), name=name, role=role,
                        capacity=round(float(capacity), 2))
        self.members.append(member)
        return member

    def get_member(self, member_id: int) -> Member:
        member = self._find_by_id(self.members, member_id)
        if member is None:
            raise TaskManagerError(f"Няма член на екипа с ID {member_id}.")
        return member

    def member_name(self, member_id: Optional[int]) -> str:
        if member_id is None:
            return "—"
        member = self._find_by_id(self.members, member_id)
        return member.name if member else "(премахнат)"

    def find_member_by_name(self, name: str, stats: Optional[dict] = None) -> Optional[Member]:
        """Двоично търсене по точно име (без значение от малки/главни букви).

        Членовете се сортират по име с Merge Sort, след което се търси двоично.
        """
        by_name = merge_sort(self.members, key=lambda m: m.name.casefold())
        index = binary_search(by_name, name.strip().casefold(),
                              key=lambda m: m.name.casefold(), stats=stats)
        return by_name[index] if index >= 0 else None

    def delete_member(self, member_id: int) -> int:
        """Премахва член на екипа. Задачите му „в процес“ се връщат в опашката."""
        member = self.get_member(member_id)
        returned = 0
        for task in self.active_tasks_of(member.id):
            self.return_to_queue(task.id)
            returned += 1
        self.members.remove(member)
        return returned

    def update_member_capacity(self, member_id: int, capacity: float) -> Member:
        member = self.get_member(member_id)
        if not 0 < capacity <= MAX_CAPACITY:
            raise TaskManagerError(f"Капацитетът трябва да е между 0 и {MAX_CAPACITY:g} ч/седмица.")
        member.capacity = round(float(capacity), 2)
        return member

    # ------------------------------------------------------------------
    # Задачи
    # ------------------------------------------------------------------
    def add_task(self, title: str, project_id: int, priority: int = 2,
                 estimate_hours: float = 1.0, deadline: Optional[str] = None,
                 description: str = "", required_role: Optional[str] = None) -> Task:
        """Създава задача и я добавя в края на опашката с чакащи задачи."""
        self.get_project(project_id)
        if required_role is not None and required_role not in ROLES:
            raise TaskManagerError("Невалидна роля.")
        task = Task(
            id=self._new_id("task"),
            title=self._clean_text(title, "Заглавие", 80),
            project_id=project_id,
            priority=self._validate_priority(priority),
            estimate_hours=self._validate_estimate(estimate_hours),
            deadline=self._validate_date(deadline),
            description=self._clean_text(description, "Описание", 300, required=False),
            required_role=required_role,
        )
        self.tasks.append(task)
        self.pending.enqueue(task)
        return task

    def get_task(self, task_id: int, stats: Optional[dict] = None) -> Task:
        task = self._find_by_id(self.tasks, task_id, stats)
        if task is None:
            raise TaskManagerError(f"Няма задача с ID {task_id}.")
        return task

    def edit_task(self, task_id: int, title: Optional[str] = None,
                  priority: Optional[int] = None, estimate_hours: Optional[float] = None,
                  deadline: Optional[str] = None, description: Optional[str] = None,
                  clear_deadline: bool = False) -> Task:
        task = self.get_task(task_id)
        # Първо валидираме всичко, после променяме – без частични промени при грешка.
        new_title = self._clean_text(title, "Заглавие", 80) if title is not None else task.title
        new_priority = self._validate_priority(priority) if priority is not None else task.priority
        new_estimate = (self._validate_estimate(estimate_hours)
                        if estimate_hours is not None else task.estimate_hours)
        new_deadline = None if clear_deadline else (
            self._validate_date(deadline) if deadline is not None else task.deadline)
        new_description = (self._clean_text(description, "Описание", 300, required=False)
                           if description is not None else task.description)
        task.title, task.priority, task.estimate_hours = new_title, new_priority, new_estimate
        task.deadline, task.description = new_deadline, new_description
        return task

    def delete_task(self, task_id: int) -> Task:
        task = self.get_task(task_id)
        self.pending.remove_if(lambda t: t.id == task_id)
        self.completed.remove_if(lambda t: t.id == task_id)
        self.tasks.remove(task)
        return task

    # ------------------------------------------------------------------
    # Опашка с чакащи задачи (Queue)
    # ------------------------------------------------------------------
    def pending_tasks(self) -> List[Task]:
        return self.pending.to_list()

    def reorder_pending_by_priority(self, algorithm: str = "quick") -> dict:
        """Пренарежда опашката: първо по приоритет, после по срок.

        Задачите се изваждат от опашката, сортират се с избрания алгоритъм
        и се връщат обратно в новия ред. Връща статистика за сравненията.
        """
        sort_fn = quick_sort if algorithm == "quick" else merge_sort
        stats = {"comparisons": 0}
        ordered = sort_fn(self.pending.to_list(), key=SORT_CRITERIA["priority"][1], stats=stats)
        self.pending.clear()
        for task in ordered:
            self.pending.enqueue(task)
        return stats

    def suggest_member(self, task: Task) -> Optional[Member]:
        """Предлага най-малко натоварения изпълнител за задачата.

        Ако задачата изисква роля и има хора с тази роля – избира измежду тях.
        """
        candidates = self.members
        if task.required_role:
            same_role = linear_search(self.members, lambda m: m.role == task.required_role)
            if same_role:
                candidates = same_role
        if not candidates:
            return None
        loads = self.all_member_loads()
        # Линейно търсене на минимума по натоварване след поемане на задачата.
        best, best_ratio = None, None
        for member in candidates:
            ratio = (loads[member.id] + task.estimate_hours) / member.capacity
            if best_ratio is None or ratio < best_ratio:
                best, best_ratio = member, ratio
        return best

    def take_next_task(self, member_id: Optional[int] = None) -> Tuple[Task, Member]:
        """Взима задачата от началото на опашката и я възлага.

        Ако не е посочен изпълнител – избира се автоматично най-малко натовареният.
        """
        if self.pending.is_empty():
            raise TaskManagerError("Няма чакащи задачи.")
        task = self.pending.peek()
        if member_id is None:
            member = self.suggest_member(task)
            if member is None:
                raise TaskManagerError("Няма членове на екипа, на които да се възложи задачата.")
        else:
            member = self.get_member(member_id)
        self.pending.dequeue()
        task.status = STATUS_IN_PROGRESS
        task.assignee_id = member.id
        return task, member

    def auto_dispatch(self) -> List[Tuple[Task, Member]]:
        """Разпределя задачи от опашката, докато има изпълнител със свободен капацитет.

        Спира при първата задача, която не може да се поеме без претоварване –
        така се спазва редът FIFO на опашката.
        """
        assigned = []
        while not self.pending.is_empty():
            task = self.pending.peek()
            member = self.suggest_member(task)
            if member is None:
                break
            if self.member_load(member.id) + task.estimate_hours > member.capacity:
                break
            assigned.append(self.take_next_task(member.id))
        return assigned

    # ------------------------------------------------------------------
    # Задачи в процес
    # ------------------------------------------------------------------
    def active_tasks(self) -> List[Task]:
        return linear_search(self.tasks, lambda t: t.status == STATUS_IN_PROGRESS)

    def active_tasks_of(self, member_id: int) -> List[Task]:
        return linear_search(self.tasks, lambda t: t.status == STATUS_IN_PROGRESS
                             and t.assignee_id == member_id)

    def reassign_task(self, task_id: int, member_id: int) -> Task:
        task = self.get_task(task_id)
        if task.status != STATUS_IN_PROGRESS:
            raise TaskManagerError("Може да се преразпределят само задачи „В процес“.")
        member = self.get_member(member_id)
        if task.assignee_id == member.id:
            raise TaskManagerError("Задачата вече е възложена на този изпълнител.")
        task.assignee_id = member.id
        return task

    def return_to_queue(self, task_id: int) -> Task:
        """Връща задача „В процес“ в края на опашката с чакащи."""
        task = self.get_task(task_id)
        if task.status != STATUS_IN_PROGRESS:
            raise TaskManagerError("В опашката може да се върне само задача „В процес“.")
        task.status = STATUS_PENDING
        task.assignee_id = None
        self.pending.enqueue(task)
        return task

    # ------------------------------------------------------------------
    # Приключени задачи (Stack)
    # ------------------------------------------------------------------
    def complete_task(self, task_id: int) -> Task:
        task = self.get_task(task_id)
        if task.status != STATUS_IN_PROGRESS:
            raise TaskManagerError("Може да се приключи само задача, която е „В процес“.")
        task.status = STATUS_DONE
        task.completed_on = date.today().isoformat()
        self.completed.push(task)
        return task

    def undo_last_completion(self) -> Task:
        """Отменя последното приключване (pop от стека)."""
        if self.completed.is_empty():
            raise TaskManagerError("Няма приключени задачи.")
        task = self.completed.pop()
        task.completed_on = None
        if task.assignee_id is not None and self._find_by_id(self.members, task.assignee_id):
            task.status = STATUS_IN_PROGRESS
        else:  # изпълнителят е премахнат -> задачата отива обратно в опашката
            task.status = STATUS_PENDING
            task.assignee_id = None
            self.pending.enqueue(task)
        return task

    def completed_tasks(self) -> List[Task]:
        """Приключените задачи – от последно приключената към най-старата."""
        return list(self.completed)

    # ------------------------------------------------------------------
    # Справки и търсене
    # ------------------------------------------------------------------
    def tasks_of_project(self, project_id: int) -> List[Task]:
        return linear_search(self.tasks, lambda t: t.project_id == project_id)

    def search_tasks(self, keyword: str, stats: Optional[dict] = None) -> List[Task]:
        """Линейно търсене по част от заглавие или описание."""
        needle = keyword.strip().casefold()
        if not needle:
            raise TaskManagerError("Въведете текст за търсене.")
        return linear_search(
            self.tasks,
            lambda t: needle in t.title.casefold() or needle in t.description.casefold(),
            stats,
        )

    def filter_tasks(self, status: Optional[str] = None, priority: Optional[int] = None,
                     member_id: Optional[int] = None, project_id: Optional[int] = None,
                     overdue_only: bool = False, today: Optional[date] = None) -> List[Task]:
        """Линейно търсене по комбинация от условия."""
        today = today or date.today()

        def matches(t: Task) -> bool:
            return ((status is None or t.status == status)
                    and (priority is None or t.priority == priority)
                    and (member_id is None or t.assignee_id == member_id)
                    and (project_id is None or t.project_id == project_id)
                    and (not overdue_only or t.is_overdue(today)))

        return linear_search(self.tasks, matches)

    def sort_tasks(self, tasks: List[Task], criterion: str,
                   algorithm: str = "quick") -> Tuple[List[Task], dict]:
        if criterion not in SORT_CRITERIA:
            raise TaskManagerError("Непознат критерий за сортиране.")
        sort_fn = quick_sort if algorithm == "quick" else merge_sort
        stats = {"comparisons": 0}
        return sort_fn(tasks, key=SORT_CRITERIA[criterion][1], stats=stats), stats

    # ------------------------------------------------------------------
    # Натоварване
    # ------------------------------------------------------------------
    def all_member_loads(self) -> Dict[int, float]:
        """Сума от оценките (часове) на задачите „В процес“ за всеки изпълнител. O(n)."""
        loads = {m.id: 0.0 for m in self.members}
        for task in self.tasks:
            if task.status == STATUS_IN_PROGRESS and task.assignee_id in loads:
                loads[task.assignee_id] += task.estimate_hours
        return loads

    def member_load(self, member_id: int) -> float:
        return self.all_member_loads().get(member_id, 0.0)

    # ------------------------------------------------------------------
    # Сериализация
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "version": 1,
            "next_ids": dict(self.next_ids),
            "projects": [p.to_dict() for p in self.projects],
            "members": [m.to_dict() for m in self.members],
            "tasks": [t.to_dict() for t in self.tasks],
            # опашката: от началото към края; стекът: от дъното към върха
            "pending_queue": [t.id for t in self.pending],
            "completed_stack": [t.id for t in self.completed.to_list()],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskManager":
        manager = cls()
        manager.projects = merge_sort([Project.from_dict(p) for p in data.get("projects", [])],
                                      key=lambda p: p.id)
        manager.members = merge_sort([Member.from_dict(m) for m in data.get("members", [])],
                                     key=lambda m: m.id)
        manager.tasks = merge_sort([Task.from_dict(t) for t in data.get("tasks", [])],
                                   key=lambda t: t.id)

        by_id = {t.id: t for t in manager.tasks}
        queued, stacked = set(), set()
        for task_id in data.get("pending_queue", []):
            task = by_id.get(task_id)
            if task is not None and task.status == STATUS_PENDING and task_id not in queued:
                manager.pending.enqueue(task)
                queued.add(task_id)
        for task_id in data.get("completed_stack", []):
            task = by_id.get(task_id)
            if task is not None and task.status == STATUS_DONE and task_id not in stacked:
                manager.completed.push(task)
                stacked.add(task_id)
        # Самопоправка при непоследователни данни (напр. ръчно редактиран файл).
        for task in manager.tasks:
            orphaned = task.status == STATUS_IN_PROGRESS and (
                task.assignee_id is None
                or manager._find_by_id(manager.members, task.assignee_id) is None)
            unknown = task.status not in (STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_DONE)
            if orphaned or unknown:
                task.status, task.assignee_id = STATUS_PENDING, None
            if task.status == STATUS_PENDING and task.id not in queued:
                manager.pending.enqueue(task)
            elif task.status == STATUS_DONE and task.id not in stacked:
                manager.completed.push(task)

        next_ids = data.get("next_ids", {})
        for kind, items in (("project", manager.projects), ("member", manager.members),
                            ("task", manager.tasks)):
            highest = items[-1].id if items else 0
            manager.next_ids[kind] = max(int(next_ids.get(kind, 1)), highest + 1)
        return manager
