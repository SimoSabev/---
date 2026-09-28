"""Конзолен потребителски интерфейс (менюта на български език)."""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, List, Optional, Sequence

from . import analytics, benchmark, storage
from .demo_data import create_demo_manager
from .manager import SORT_CRITERIA, TaskManager, TaskManagerError
from .models import (
    PRIORITY_LABELS, ROLES, STATUS_DONE, STATUS_IN_PROGRESS, STATUS_LABELS, STATUS_PENDING, Task,
)

REPORTS_DIR = storage.BASE_DIR / "reports"


class Cancel(Exception):
    """Потребителят отказа текущата операция."""


# ---------------------------------------------------------------------------
# Форматиране
# ---------------------------------------------------------------------------
def fmt_date(iso: Optional[str]) -> str:
    return date.fromisoformat(iso).strftime("%d.%m.%Y") if iso else "—"


def fmt_hours(hours: float) -> str:
    return f"{hours:g} ч"


def shorten(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


def short_name(name: str) -> str:
    """„Десислава Иванова“ -> „Десислава И.“"""
    parts = name.split()
    return f"{parts[0]} {parts[-1][0]}." if len(parts) > 1 else name


def print_table(headers: Sequence[str], rows: List[Sequence], max_width: int = 34) -> None:
    if not rows:
        print("  (няма записи)")
        return
    cells = [[shorten(str(c), max_width) for c in row] for row in rows]
    widths = [len(h) for h in headers]
    for row in cells:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    line = "  " + "─┼─".join("─" * w for w in widths)
    print("  " + " │ ".join(h.ljust(w) for h, w in zip(headers, widths)))
    print(line)
    for row in cells:
        print("  " + " │ ".join(c.ljust(w) for c, w in zip(row, widths)))


def title(text: str) -> None:
    print()
    print("═" * 72)
    print(f"  {text}")
    print("═" * 72)


def info(text: str) -> None:
    print(f"  ✔ {text}")


def warn(text: str) -> None:
    print(f"  ⚠ {text}")


# ---------------------------------------------------------------------------
# Въвеждане
# ---------------------------------------------------------------------------
def _read(prompt: str) -> str:
    return input(f"  {prompt}").strip()


def ask_text(prompt: str, required: bool = True) -> str:
    value = _read(f"{prompt}: ")
    if not value and required:
        raise Cancel
    return value


def ask_int(prompt: str, lo: int, hi: int, required: bool = True,
            default: Optional[int] = None) -> Optional[int]:
    while True:
        raw = _read(f"{prompt}: ")
        if not raw:
            if default is not None:
                return default
            if required:
                raise Cancel
            return None
        try:
            value = int(raw)
        except ValueError:
            warn("Въведете цяло число.")
            continue
        if lo <= value <= hi:
            return value
        warn(f"Числото трябва да е между {lo} и {hi}.")


def ask_float(prompt: str, lo: float, hi: float, required: bool = True,
              default: Optional[float] = None) -> Optional[float]:
    while True:
        raw = _read(f"{prompt}: ").replace(",", ".")
        if not raw:
            if default is not None:
                return default
            if required:
                raise Cancel
            return None
        try:
            value = float(raw)
        except ValueError:
            warn("Въведете число (напр. 8 или 2.5).")
            continue
        if lo < value <= hi:
            return value
        warn(f"Числото трябва да е по-голямо от {lo:g} и най-много {hi:g}.")


def parse_user_date(raw: str) -> str:
    """Приема ДД.ММ.ГГГГ, ГГГГ-ММ-ДД или +N (след N дни). Връща ISO дата."""
    raw = raw.strip()
    if raw.startswith("+") and raw[1:].isdigit():
        return (date.today() + timedelta(days=int(raw[1:]))).isoformat()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d.%m.%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(raw)


def ask_date(prompt: str, required: bool = False) -> Optional[str]:
    while True:
        raw = _read(f"{prompt} (ДД.ММ.ГГГГ или +дни): ")
        if not raw:
            if required:
                raise Cancel
            return None
        try:
            return parse_user_date(raw)
        except ValueError:
            warn("Невалидна дата. Пример: 25.12.2026 или +7")


def ask_choice(header: str, options: Sequence[str], allow_none: bool = False,
               none_label: str = "без") -> Optional[int]:
    """Показва номериран списък. Връща индекс (от 0) или None."""
    print(f"  {header}")
    for i, option in enumerate(options, 1):
        print(f"    {i}. {option}")
    if allow_none:
        print(f"    0. {none_label}")
    choice = ask_int("Избор", 0 if allow_none else 1, len(options))
    return None if choice == 0 else choice - 1


def confirm(prompt: str) -> bool:
    return _read(f"{prompt} (д/н): ").casefold() in ("д", "да", "y", "yes")


def pause() -> None:
    _read("Натиснете Enter за продължение...")


# ---------------------------------------------------------------------------
# Потребителски интерфейс
# ---------------------------------------------------------------------------
class ConsoleUI:
    def __init__(self, manager: TaskManager, data_path: Path = storage.DATA_FILE) -> None:
        self.m = manager
        self.data_path = Path(data_path)

    # ---------------- общи ----------------
    def save(self) -> None:
        try:
            storage.save(self.m, self.data_path)
        except OSError as error:
            warn(f"Данните не можаха да се запишат: {error}")

    def menu(self, header: str, items: List[tuple], show: Optional[Callable] = None) -> None:
        """Цикъл на подменю. items: [(етикет, функция), ...]."""
        while True:
            title(header)
            if show:
                show()
            for i, (label, _) in enumerate(items, 1):
                print(f"  {i:>2}. {label}")
            print("   0. Назад")
            try:
                choice = ask_int("Избор", 0, len(items), default=0)
            except Cancel:
                return
            if choice == 0:
                return
            self.run_action(items[choice - 1][1])

    def run_action(self, action: Callable) -> None:
        print()
        try:
            action()
        except Cancel:
            warn("Операцията е отказана.")
        except TaskManagerError as error:
            warn(f"Грешка: {error}")
        self.save()
        pause()

    def run(self, startup_message: str = "") -> None:
        if startup_message:
            print(f"\n  {startup_message}")
        items = [
            ("Проекти", self.projects_menu),
            ("Екип (изпълнители)", self.team_menu),
            ("Задачи", self.tasks_menu),
            ("Чакащи задачи (опашка / queue)", self.queue_menu),
            ("Приключени задачи (стек / stack)", self.stack_menu),
            ("Търсене (линейно / двоично)", self.search_menu),
            ("Сортиране (Quick Sort / Merge Sort)", self.sort_menu),
            ("Анализ на натоварването", self.analysis_menu),
            ("Сравнение на алгоритмите", self.benchmark_menu),
            ("Данни (запис, зареждане, демо)", self.data_menu),
        ]
        while True:
            print()
            print("╔" + "═" * 70 + "╗")
            print("║" + "СИСТЕМА ЗА УПРАВЛЕНИЕ НА ЗАДАЧИ НА AI ЕКИП".center(70) + "║")
            print("╚" + "═" * 70 + "╝")
            self.print_dashboard()
            for i, (label, _) in enumerate(items, 1):
                print(f"  {i:>2}. {label}")
            print("   0. Изход")
            try:
                choice = ask_int("Избор", 0, len(items))
            except Cancel:
                continue
            if choice == 0:
                self.save()
                print("\n  Данните са записани. Довиждане!\n")
                return
            items[choice - 1][1]()

    def print_dashboard(self) -> None:
        s = analytics.team_summary(self.m)
        print(f"  Проекти: {len(self.m.projects)}  |  Екип: {len(self.m.members)}  |  "
              f"Чакащи: {s.pending_count}  |  В процес: {s.active_count}  |  "
              f"Приключени: {s.done_count}  |  Просрочени: {s.overdue_count}")
        print(f"  Натоварване на екипа: {analytics.progress_bar(s.team_utilization)} "
              f"{s.team_utilization:.0%}")
        print("  " + "─" * 70)

    # ---------------- визуализация ----------------
    def task_rows(self, tasks: List[Task], numbered: bool = False,
                  show_status: bool = True) -> None:
        """Таблица със задачи (до ~120 символа – побира се в стандартна конзола)."""
        today = date.today()
        rows = []
        for i, t in enumerate(tasks, 1):
            deadline = fmt_date(t.deadline) + (" !" if t.is_overdue(today) else "")
            row = [t.id, shorten(t.title, 26), shorten(self.project_name(t.project_id), 18),
                   t.priority_label, fmt_hours(t.estimate_hours), deadline]
            if show_status:
                row.append(t.status_label)
            row.append(short_name(self.m.member_name(t.assignee_id)))
            rows.append(([i] if numbered else []) + row)
        headers = ["ID", "Заглавие", "Проект", "Приоритет", "Оценка", "Срок"]
        headers += ["Статус"] if show_status else []
        headers += ["Изпълнител"]
        print_table((["№"] if numbered else []) + headers, rows)
        if any(t.is_overdue(today) for t in tasks):
            print("  (! = просрочен срок)")

    def project_name(self, project_id: int) -> str:
        try:
            return self.m.get_project(project_id).name
        except TaskManagerError:
            return "(изтрит)"

    def show_task_details(self, t: Task) -> None:
        print(f"  Задача #{t.id}: {t.title}")
        print(f"    Проект:          {self.project_name(t.project_id)}")
        print(f"    Приоритет:       {t.priority_label}")
        print(f"    Оценка:          {fmt_hours(t.estimate_hours)}")
        print(f"    Краен срок:      {fmt_date(t.deadline)}"
              + ("  (ПРОСРОЧЕНА)" if t.is_overdue() else ""))
        print(f"    Нужна роля:      {t.required_role or '—'}")
        print(f"    Статус:          {t.status_label}")
        print(f"    Изпълнител:      {self.m.member_name(t.assignee_id)}")
        print(f"    Създадена на:    {fmt_date(t.created_on)}")
        if t.completed_on:
            print(f"    Приключена на:   {fmt_date(t.completed_on)}")
        if t.description:
            print(f"    Описание:        {t.description}")

    def show_members(self) -> None:
        loads = {x.member.id: x for x in analytics.member_loads(self.m)}
        rows = []
        for member in self.m.members:
            x = loads[member.id]
            rows.append([member.id, member.name, member.role,
                         f"{x.active_hours:g}/{member.capacity:g} ч",
                         f"{x.utilization:.0%}", x.level])
        print_table(["ID", "Име", "Роля", "Натоварване", "%", "Ниво"], rows)

    def show_projects(self) -> None:
        rows = []
        for p in analytics.project_progress(self.m):
            rows.append([p.project.id, p.project.name, fmt_date(p.project.deadline),
                         f"{p.done}/{p.total}", f"{p.percent:.0%}", p.risk])
        print_table(["ID", "Проект", "Срок", "Приключени", "Напредък", "Състояние"], rows)

    # ---------------- избор на обект ----------------
    def pick_project(self, prompt: str = "ID на проект") -> int:
        if not self.m.projects:
            raise TaskManagerError("Няма проекти. Първо създайте проект.")
        print_table(["ID", "Проект"], [[p.id, p.name] for p in self.m.projects])
        return ask_int(prompt, 1, 10 ** 9)

    def pick_member(self, prompt: str = "ID на изпълнител", required: bool = True,
                    default: Optional[int] = None) -> Optional[int]:
        if not self.m.members:
            raise TaskManagerError("Няма членове на екипа. Първо добавете изпълнител.")
        self.show_members()
        return ask_int(prompt, 1, 10 ** 9, required=required, default=default)

    def pick_task(self, tasks: List[Task], prompt: str = "ID на задача") -> int:
        if not tasks:
            raise TaskManagerError("Няма подходящи задачи.")
        self.task_rows(tasks)
        return ask_int(prompt, 1, 10 ** 9)

    # =====================================================================
    # 1. Проекти
    # =====================================================================
    def projects_menu(self) -> None:
        self.menu("ПРОЕКТИ", [
            ("Списък с проекти и напредък", self.show_projects),
            ("Нов проект", self.add_project),
            ("Задачи по проект", self.project_tasks),
            ("Изтриване на проект", self.delete_project),
        ])

    def add_project(self) -> None:
        print("  (Оставете задължително поле празно, за да откажете.)")
        name = ask_text("Име на проекта")
        description = ask_text("Описание [по избор]", required=False)
        deadline = ask_date("Краен срок [по избор]")
        project = self.m.add_project(name, description, deadline)
        info(f"Създаден проект #{project.id} „{project.name}“.")

    def project_tasks(self) -> None:
        project_id = self.pick_project()
        project = self.m.get_project(project_id)
        print(f"\n  Задачи в проект „{project.name}“:")
        tasks, _ = self.m.sort_tasks(self.m.tasks_of_project(project_id), "priority", "quick")
        self.task_rows(tasks)

    def delete_project(self) -> None:
        project = self.m.get_project(self.pick_project())
        count = len(self.m.tasks_of_project(project.id))
        if confirm(f"Изтриване на „{project.name}“ и неговите {count} задачи?"):
            self.m.delete_project(project.id)
            info("Проектът е изтрит.")
        else:
            raise Cancel

    # =====================================================================
    # 2. Екип
    # =====================================================================
    def team_menu(self) -> None:
        self.menu("ЕКИП (ИЗПЪЛНИТЕЛИ)", [
            ("Списък с екипа и натоварване", self.show_members),
            ("Нов член на екипа", self.add_member),
            ("Промяна на капацитет", self.change_capacity),
            ("Задачи на изпълнител", self.member_tasks),
            ("Премахване на член", self.delete_member),
        ])

    def add_member(self) -> None:
        print("  (Оставете задължително поле празно, за да откажете.)")
        name = ask_text("Име и фамилия")
        role = ROLES[ask_choice("Роля:", ROLES)]
        capacity = ask_float("Капацитет в часове/седмица [Enter = 40]", 0, 80, default=40)
        member = self.m.add_member(name, role, capacity)
        info(f"Добавен {member.name} (#{member.id}, {member.role}).")

    def change_capacity(self) -> None:
        member_id = self.pick_member()
        capacity = ask_float("Нов капацитет (ч/седмица)", 0, 80)
        member = self.m.update_member_capacity(member_id, capacity)
        info(f"Капацитетът на {member.name} е {member.capacity:g} ч/седмица.")

    def member_tasks(self) -> None:
        member = self.m.get_member(self.pick_member())
        tasks = self.m.filter_tasks(member_id=member.id)
        tasks, _ = self.m.sort_tasks(tasks, "deadline", "merge")
        print(f"\n  Задачи на {member.name} ({member.role}):")
        self.task_rows(tasks)

    def delete_member(self) -> None:
        member = self.m.get_member(self.pick_member())
        if not confirm(f"Премахване на {member.name}? Задачите му в процес ще се върнат в опашката."):
            raise Cancel
        returned = self.m.delete_member(member.id)
        info(f"{member.name} е премахнат/а. Върнати в опашката задачи: {returned}.")

    # =====================================================================
    # 3. Задачи
    # =====================================================================
    def tasks_menu(self) -> None:
        self.menu("ЗАДАЧИ", [
            ("Всички задачи", lambda: self.task_rows(self.m.tasks)),
            ("Задачи в процес", lambda: self.task_rows(self.m.active_tasks(), show_status=False)),
            ("Нова задача (добавя се в опашката)", self.add_task),
            ("Детайли за задача", self.task_details),
            ("Редактиране на задача", self.edit_task),
            ("Приключване на задача (push в стека)", self.complete_task),
            ("Преразпределяне към друг изпълнител", self.reassign_task),
            ("Връщане в опашката", self.return_task),
            ("Изтриване на задача", self.delete_task),
        ])

    def add_task(self) -> None:
        print("  (Оставете задължително поле празно, за да откажете.)")
        project_id = self.pick_project()
        self.m.get_project(project_id)
        task_title = ask_text("Заглавие")
        description = ask_text("Описание [по избор]", required=False)
        priority = ask_choice("Приоритет:", list(PRIORITY_LABELS.values())) + 1
        estimate = ask_float("Оценка в часове", 0, 500)
        deadline = ask_date("Краен срок [по избор]")
        role_index = ask_choice("Необходима роля:", ROLES, allow_none=True,
                                none_label="без изискване")
        role = ROLES[role_index] if role_index is not None else None
        task = self.m.add_task(task_title, project_id, priority, estimate, deadline,
                               description, role)
        info(f"Задача #{task.id} е добавена в края на опашката "
             f"(позиция {len(self.m.pending)}).")

    def task_details(self) -> None:
        task_id = ask_int("ID на задача", 1, 10 ** 9)
        self.show_task_details(self.m.get_task(task_id))

    def edit_task(self) -> None:
        task = self.m.get_task(ask_int("ID на задача", 1, 10 ** 9))
        self.show_task_details(task)
        print("\n  Натиснете Enter, за да запазите текущата стойност.")
        new_title = ask_text("Ново заглавие", required=False) or None
        new_description = ask_text("Ново описание", required=False) or None
        priority_index = ask_choice("Нов приоритет:", list(PRIORITY_LABELS.values()),
                                    allow_none=True, none_label="без промяна")
        estimate = ask_float("Нова оценка в часове", 0, 500, required=False)
        raw = _read("Нов срок (ДД.ММ.ГГГГ, +дни, „-“ = премахване): ")
        deadline, clear = None, False
        if raw == "-":
            clear = True
        elif raw:
            try:
                deadline = parse_user_date(raw)
            except ValueError:
                raise TaskManagerError(f"Невалидна дата: {raw}") from None
        self.m.edit_task(task.id, title=new_title,
                         priority=None if priority_index is None else priority_index + 1,
                         estimate_hours=estimate, deadline=deadline,
                         description=new_description, clear_deadline=clear)
        info("Задачата е обновена.")

    def complete_task(self) -> None:
        task_id = self.pick_task(self.m.active_tasks())
        task = self.m.complete_task(task_id)
        info(f"Задача #{task.id} „{task.title}“ е приключена и добавена на върха на стека.")

    def reassign_task(self) -> None:
        task = self.m.get_task(self.pick_task(self.m.active_tasks()))
        suggestion = self.m.suggest_member(task)
        if suggestion is not None:
            print(f"  Препоръка: {suggestion.name} (#{suggestion.id})")
        member_id = self.pick_member("ID на новия изпълнител")
        self.m.reassign_task(task.id, member_id)
        info(f"Задача #{task.id} е възложена на {self.m.member_name(member_id)}.")

    def return_task(self) -> None:
        task = self.m.return_to_queue(self.pick_task(self.m.active_tasks()))
        info(f"Задача #{task.id} е върната в края на опашката.")

    def delete_task(self) -> None:
        task = self.m.get_task(ask_int("ID на задача", 1, 10 ** 9))
        if not confirm(f"Изтриване на задача #{task.id} „{task.title}“?"):
            raise Cancel
        self.m.delete_task(task.id)
        info("Задачата е изтрита.")

    # =====================================================================
    # 4. Опашка
    # =====================================================================
    def queue_menu(self) -> None:
        self.menu("ЧАКАЩИ ЗАДАЧИ – ОПАШКА (FIFO)", [
            ("Покажи опашката", self.show_queue),
            ("Поеми следващата задача (dequeue)", self.take_next),
            ("Автоматично разпределение по свободен капацитет", self.auto_dispatch),
            ("Пренареди опашката по приоритет", self.reorder_queue),
        ], show=lambda: print(f"  В опашката: {len(self.m.pending)} задачи\n"))

    def show_queue(self) -> None:
        pending = self.m.pending_tasks()
        print("  Начало на опашката ↓ (първата задача се поема първа)")
        self.task_rows(pending, numbered=True, show_status=False)
        if pending:
            hours = sum(t.estimate_hours for t in pending)
            print(f"\n  Общо: {len(pending)} задачи, {hours:g} ч работа.")

    def take_next(self) -> None:
        if self.m.pending.is_empty():
            raise TaskManagerError("Опашката е празна.")
        task = self.m.pending.peek()
        print("  Следваща задача в опашката:")
        self.show_task_details(task)
        suggestion = self.m.suggest_member(task)
        if suggestion is None:
            raise TaskManagerError("Няма членове на екипа.")
        print()
        member_id = self.pick_member(
            f"ID на изпълнител [Enter = препоръчан: {suggestion.name}]", default=suggestion.id)
        task, member = self.m.take_next_task(member_id)
        load = self.m.member_load(member.id)
        info(f"Задача #{task.id} е възложена на {member.name} "
             f"(натоварване {load:g}/{member.capacity:g} ч).")
        if load > member.capacity:
            warn(f"{member.name} вече е претоварен/а!")

    def auto_dispatch(self) -> None:
        assigned = self.m.auto_dispatch()
        if not assigned:
            warn("Нито една задача не беше разпределена (опашката е празна или "
                 "няма свободен капацитет за първата задача).")
            return
        for task, member in assigned:
            info(f"#{task.id} „{shorten(task.title, 40)}“ → {member.name}")
        if not self.m.pending.is_empty():
            print(f"\n  Останали в опашката: {len(self.m.pending)} "
                  f"(няма свободен капацитет за следващата задача).")

    def reorder_queue(self) -> None:
        index = ask_choice("Алгоритъм:", ["Quick Sort", "Merge Sort"])
        algorithm = "quick" if index == 0 else "merge"
        stats = self.m.reorder_pending_by_priority(algorithm)
        info(f"Опашката е пренаредена по приоритет и срок "
             f"({stats['comparisons']} сравнения).")
        self.show_queue()

    # =====================================================================
    # 5. Стек
    # =====================================================================
    def stack_menu(self) -> None:
        self.menu("ПРИКЛЮЧЕНИ ЗАДАЧИ – СТЕК (LIFO)", [
            ("Покажи приключените (от най-новата)", self.show_stack),
            ("Последно приключена задача (peek)", self.peek_stack),
            ("Отмени последното приключване (pop)", self.undo_completion),
        ], show=lambda: print(f"  В стека: {len(self.m.completed)} задачи\n"))

    def show_stack(self) -> None:
        print("  Връх на стека ↓")
        self.task_rows(self.m.completed_tasks(), numbered=True, show_status=False)

    def peek_stack(self) -> None:
        if self.m.completed.is_empty():
            raise TaskManagerError("Няма приключени задачи.")
        self.show_task_details(self.m.completed.peek())

    def undo_completion(self) -> None:
        if self.m.completed.is_empty():
            raise TaskManagerError("Няма приключени задачи.")
        task = self.m.completed.peek()
        if not confirm(f"Отмяна на приключването на #{task.id} „{task.title}“?"):
            raise Cancel
        task = self.m.undo_last_completion()
        info(f"Задача #{task.id} отново е със статус „{task.status_label}“.")

    # =====================================================================
    # 6. Търсене
    # =====================================================================
    def search_menu(self) -> None:
        self.menu("ТЪРСЕНЕ", [
            ("Задача по ID (двоично търсене)", self.search_by_id),
            ("Задачи по ключова дума (линейно търсене)", self.search_keyword),
            ("Изпълнител по име (двоично търсене)", self.search_member),
            ("Филтриране на задачи (линейно търсене)", self.search_filter),
        ])

    def search_by_id(self) -> None:
        task_id = ask_int("ID на задача", 1, 10 ** 9)
        stats = {"comparisons": 0}
        try:
            task = self.m.get_task(task_id, stats)
        finally:
            print(f"  Двоично търсене: {stats['comparisons']} стъпки "
                  f"при {len(self.m.tasks)} задачи.")
        self.show_task_details(task)

    def search_keyword(self) -> None:
        keyword = ask_text("Ключова дума")
        stats = {"comparisons": 0}
        found = self.m.search_tasks(keyword, stats)
        print(f"  Линейно търсене: проверени {stats['comparisons']} задачи, "
              f"намерени {len(found)}.")
        self.task_rows(found)

    def search_member(self) -> None:
        name = ask_text("Точно име на изпълнител")
        stats = {"comparisons": 0}
        member = self.m.find_member_by_name(name, stats)
        print(f"  Двоично търсене: {stats['comparisons']} стъпки при {len(self.m.members)} души.")
        if member is None:
            partial = [x for x in self.m.members if name.casefold() in x.name.casefold()]
            warn("Няма точно съвпадение." + (" Подобни: " + ", ".join(x.name for x in partial)
                                              if partial else ""))
            return
        print(f"  Намерен: #{member.id} {member.name} – {member.role}, "
              f"{self.m.member_load(member.id):g}/{member.capacity:g} ч")
        self.task_rows(self.m.filter_tasks(member_id=member.id))

    def search_filter(self) -> None:
        print("  Изберете условия (0 = без значение).")
        statuses = [STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_DONE]
        s_index = ask_choice("Статус:", [STATUS_LABELS[s] for s in statuses],
                             allow_none=True, none_label="всички")
        p_index = ask_choice("Приоритет:", list(PRIORITY_LABELS.values()),
                             allow_none=True, none_label="всички")
        member_id = None
        if self.m.members and confirm("Филтър по изпълнител?"):
            member_id = self.pick_member()
        project_id = None
        if self.m.projects and confirm("Филтър по проект?"):
            project_id = self.pick_project()
        overdue = confirm("Само просрочени?")
        found = self.m.filter_tasks(
            status=None if s_index is None else statuses[s_index],
            priority=None if p_index is None else p_index + 1,
            member_id=member_id, project_id=project_id, overdue_only=overdue)
        print(f"\n  Намерени: {len(found)}")
        self.task_rows(found)

    # =====================================================================
    # 7. Сортиране
    # =====================================================================
    def sort_menu(self) -> None:
        self.menu("СОРТИРАНЕ НА ЗАДАЧИ", [("Сортирай задачи", self.sort_tasks)])

    def sort_tasks(self) -> None:
        groups = [
            ("Всички задачи", lambda: self.m.tasks),
            ("Чакащи задачи", self.m.pending_tasks),
            ("Задачи в процес", self.m.active_tasks),
            ("Приключени задачи", self.m.completed_tasks),
        ]
        group = ask_choice("Кои задачи:", [g[0] for g in groups])
        keys = list(SORT_CRITERIA)
        criterion = keys[ask_choice("Критерий:", [SORT_CRITERIA[k][0] for k in keys])]
        algorithm = ["quick", "merge"][ask_choice("Алгоритъм:", ["Quick Sort", "Merge Sort"])]
        tasks = list(groups[group][1]())
        result, stats = self.m.sort_tasks(tasks, criterion, algorithm)
        name = "Quick Sort" if algorithm == "quick" else "Merge Sort"
        print(f"\n  {name}: {len(tasks)} задачи, {stats['comparisons']} сравнения.\n")
        self.task_rows(result, numbered=group != 0, show_status=group == 0)

    # =====================================================================
    # 8. Анализ
    # =====================================================================
    def analysis_menu(self) -> None:
        self.menu("АНАЛИЗ НА НАТОВАРВАНЕТО", [
            ("Пълен анализ", self.show_analysis),
            ("Експорт на отчет в текстов файл", self.export_report),
        ])

    def show_analysis(self) -> None:
        loads = analytics.member_loads(self.m)
        s = analytics.team_summary(self.m, loads)
        print("  ОБОБЩЕНИЕ")
        print(f"    Общ капацитет:          {s.total_capacity:g} ч/седмица ({s.member_count} души)")
        print(f"    В процес:               {s.active_count} задачи, {s.active_hours:g} ч")
        print(f"    Чакащи (опашка):        {s.pending_count} задачи, {s.pending_hours:g} ч")
        print(f"    Приключени (стек):      {s.done_count}")
        print(f"    Просрочени:             {s.overdue_count}")
        print(f"    Натоварване на екипа:   {s.team_utilization:.0%}")
        print(f"    Дисбаланс (макс − мин): {s.imbalance:.0%}")
        if s.weeks_to_clear != float("inf"):
            print(f"    Време за изчистване:    ~{s.weeks_to_clear:.1f} седмици")

        print("\n  НАТОВАРВАНЕ ПО ИЗПЪЛНИТЕЛИ (сортирано с Merge Sort)")
        for x in loads:
            print(f"    {shorten(x.member.name, 22):<22} {analytics.progress_bar(x.utilization)} "
                  f"{x.utilization:>5.0%}  {x.active_hours:g}/{x.member.capacity:g} ч  "
                  f"[{x.level}]")
        if not loads:
            print("    (няма членове на екипа)")

        print("\n  ПРИКЛЮЧЕНА РАБОТА ПО ИЗПЪЛНИТЕЛИ")
        print_table(["Изпълнител", "Роля", "В процес", "Приключени", "Приключени ч",
                     "Просрочени", "Критични"],
                    [[x.member.name, x.member.role, x.active_count, x.done_count,
                      f"{x.done_hours:g}", x.overdue_count, x.critical_count] for x in loads])

        print("\n  НАПРЕДЪК ПО ПРОЕКТИ (по изработени часове)")
        for p in analytics.project_progress(self.m):
            days = ""
            if p.days_left is not None:
                days = (f"остават {p.days_left} дни" if p.days_left >= 0
                        else f"просрочен с {-p.days_left} дни")
            print(f"    {shorten(p.project.name, 26):<26} {analytics.progress_bar(p.percent)} "
                  f"{p.percent:>5.0%}  {p.done}/{p.total} задачи  [{p.risk}] {days}")

        print("\n  ПРЕПОРЪКИ")
        for tip in analytics.recommendations(self.m, loads):
            print(f"    • {tip}")

    def export_report(self) -> None:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        path = REPORTS_DIR / f"otchet_{datetime.now():%Y%m%d_%H%M%S}.txt"
        try:
            path.write_text(analytics.build_text_report(self.m), encoding="utf-8")
        except OSError as error:
            raise TaskManagerError(f"Отчетът не можа да се запише: {error}") from None
        info(f"Отчетът е записан в: {path}")

    # =====================================================================
    # 9. Сравнение на алгоритмите
    # =====================================================================
    def benchmark_menu(self) -> None:
        self.menu("СРАВНЕНИЕ НА АЛГОРИТМИТЕ", [
            ("Quick Sort срещу Merge Sort", self.benchmark_sorting),
            ("Линейно срещу двоично търсене", self.benchmark_searching),
        ])

    def benchmark_sorting(self) -> None:
        n = ask_int("Брой елементи [Enter = 2000]", 10, 50000, default=2000)
        theory = f"{round(n * math.log2(n)):,}".replace(",", " ")
        print(f"\n  Сортиране на {n} елемента (приоритет, часове). "
              f"Теоретично n·log2(n) ≈ {theory} сравнения.")
        rows = []
        for r in benchmark.compare_sorting(n):
            rows.append([r["data"], r["algorithm"], f"{r['comparisons']:,}".replace(",", " "),
                         f"{r['time_ms']:.1f} ms", "да" if r["correct"] else "НЕ"])
        print_table(["Данни", "Алгоритъм", "Сравнения", "Време", "Коректно"], rows)
        print("\n  Извод: при случайни данни Quick Sort обикновено прави по-малко сравнения;")
        print("  Merge Sort е стабилен, гарантирано O(n log n) и се справя по-добре с вече")
        print("  подредени данни. Медианата от три пази Quick Sort от O(n²) при сортиран вход,")
        print("  а тристранното разделяне – при много еднакви ключове (приоритети 1..4).")

    def benchmark_searching(self) -> None:
        n = ask_int("Брой елементи [Enter = 10000]", 10, 1000000, default=10000)
        r = benchmark.compare_searching(n)
        print_table(["Алгоритъм", "Средно сравнения", "Сложност", "Общо време (200 търсения)"], [
            ["Линейно търсене", f"{r['linear_avg']:.1f}", "O(n)", f"{r['linear_ms']:.1f} ms"],
            ["Двоично търсене", f"{r['binary_avg']:.1f}", "O(log n)", f"{r['binary_ms']:.1f} ms"],
        ])
        print(f"\n  log2({n}) ≈ {r['log2n']:.1f} – двоичното търсене прави най-много толкова стъпки,")
        print(f"  докато линейното прави средно около n/2 ≈ {n / 2:g}.")

    # =====================================================================
    # 10. Данни
    # =====================================================================
    def data_menu(self) -> None:
        self.menu("ДАННИ", [
            ("Запиши сега", lambda: (self.save(), info(f"Записано в {self.data_path}"))),
            ("Зареди отново от файла", self.reload),
            ("Възстанови демонстрационните данни", self.reset_demo),
            ("Изчисти всички данни", self.clear_all),
        ])

    def reload(self) -> None:
        self.m, message = storage.load(self.data_path)
        info(message)

    def reset_demo(self) -> None:
        if not confirm("Текущите данни ще бъдат заменени с демо данни. Продължаване?"):
            raise Cancel
        self.m = create_demo_manager()
        info("Демонстрационните данни са заредени.")

    def clear_all(self) -> None:
        if not confirm("ВСИЧКИ проекти, хора и задачи ще бъдат изтрити. Сигурни ли сте?"):
            raise Cancel
        self.m = TaskManager()
        info("Системата е празна.")
