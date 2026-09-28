"""Тестове за бизнес логиката, анализа и записа на данни."""

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from task_manager import analytics, storage
from task_manager.demo_data import create_demo_manager
from task_manager.manager import TaskManager, TaskManagerError
from task_manager.models import STATUS_DONE, STATUS_IN_PROGRESS, STATUS_PENDING


def _days(n):
    return (date.today() + timedelta(days=n)).isoformat()


class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.m = TaskManager()
        self.p = self.m.add_project("Проект", "описание", _days(30))
        self.ana = self.m.add_member("Ана", "ML инженер", 20)
        self.bob = self.m.add_member("Борис", "Data инженер", 40)

    def add(self, title="Задача", priority=2, hours=5, deadline=None, role=None):
        return self.m.add_task(title, self.p.id, priority, hours, deadline, required_role=role)

    # --- валидация ---
    def test_validation_errors(self):
        with self.assertRaises(TaskManagerError):
            self.m.add_project("  ")
        with self.assertRaises(TaskManagerError):
            self.m.add_project("проект")  # дублирано име (без значение от регистъра)
        with self.assertRaises(TaskManagerError):
            self.m.add_member("Ана", "ML инженер")
        with self.assertRaises(TaskManagerError):
            self.m.add_member("Нов", "Непозната роля")
        with self.assertRaises(TaskManagerError):
            self.m.add_member("Нов", "ML инженер", 0)
        with self.assertRaises(TaskManagerError):
            self.add(priority=9)
        with self.assertRaises(TaskManagerError):
            self.add(hours=0)
        with self.assertRaises(TaskManagerError):
            self.m.add_task("x", 999)
        with self.assertRaises(TaskManagerError):
            self.add(deadline="31.02.2026")

    # --- опашка ---
    def test_new_tasks_go_to_queue_in_fifo_order(self):
        t1, t2, t3 = self.add("1"), self.add("2"), self.add("3")
        self.assertEqual([t.id for t in self.m.pending_tasks()], [t1.id, t2.id, t3.id])
        task, member = self.m.take_next_task(self.bob.id)
        self.assertIs(task, t1)
        self.assertEqual(task.status, STATUS_IN_PROGRESS)
        self.assertEqual(task.assignee_id, self.bob.id)
        self.assertEqual(len(self.m.pending), 2)

    def test_take_next_on_empty_queue(self):
        with self.assertRaises(TaskManagerError):
            self.m.take_next_task()

    def test_auto_assign_prefers_role_and_low_load(self):
        self.add(role="ML инженер")
        task, member = self.m.take_next_task()
        self.assertEqual(member.id, self.ana.id)
        self.add()  # без роля -> по-малко натовареният (Борис: 0/40)
        task, member = self.m.take_next_task()
        self.assertEqual(member.id, self.bob.id)

    def test_reorder_queue_by_priority(self):
        low = self.add("low", 1, deadline=_days(1))
        crit = self.add("crit", 4, deadline=_days(10))
        high_late = self.add("high late", 3, deadline=_days(20))
        high_soon = self.add("high soon", 3, deadline=_days(2))
        for algorithm in ("quick", "merge"):
            stats = self.m.reorder_pending_by_priority(algorithm)
            self.assertGreater(stats["comparisons"], 0)
            self.assertEqual([t.id for t in self.m.pending_tasks()],
                             [crit.id, high_soon.id, high_late.id, low.id])

    def test_auto_dispatch_respects_capacity(self):
        self.add(hours=15, role="ML инженер")   # Ана 15/20
        self.add(hours=30, role="Data инженер")  # Борис 30/40
        self.add(hours=15, role="ML инженер")   # Ана би станала 30/20 -> спира
        assigned = self.m.auto_dispatch()
        self.assertEqual(len(assigned), 2)
        self.assertEqual(len(self.m.pending), 1)
        self.assertLessEqual(self.m.member_load(self.ana.id), self.ana.capacity)

    # --- стек ---
    def test_complete_and_undo_uses_stack(self):
        t1, t2 = self.add("1"), self.add("2")
        self.m.take_next_task(self.ana.id)
        self.m.take_next_task(self.bob.id)
        with self.assertRaises(TaskManagerError):
            self.m.complete_task(self.add("3").id)  # чакаща задача не може да се приключи
        self.m.complete_task(t1.id)
        self.m.complete_task(t2.id)
        self.assertEqual([t.id for t in self.m.completed_tasks()], [t2.id, t1.id])
        undone = self.m.undo_last_completion()
        self.assertIs(undone, t2)
        self.assertEqual(t2.status, STATUS_IN_PROGRESS)
        self.assertIsNone(t2.completed_on)
        self.assertEqual(t1.status, STATUS_DONE)

    def test_undo_when_assignee_removed_returns_to_queue(self):
        t = self.add()
        self.m.take_next_task(self.ana.id)
        self.m.complete_task(t.id)
        self.m.delete_member(self.ana.id)
        self.m.undo_last_completion()
        self.assertEqual(t.status, STATUS_PENDING)
        self.assertIn(t, self.m.pending_tasks())

    def test_undo_on_empty_stack(self):
        with self.assertRaises(TaskManagerError):
            self.m.undo_last_completion()

    # --- други операции ---
    def test_delete_member_returns_tasks_to_queue(self):
        t = self.add()
        self.m.take_next_task(self.ana.id)
        self.assertEqual(self.m.delete_member(self.ana.id), 1)
        self.assertEqual(t.status, STATUS_PENDING)
        self.assertIsNone(t.assignee_id)
        self.assertEqual(self.m.pending_tasks(), [t])

    def test_delete_task_everywhere(self):
        t1, t2 = self.add("1"), self.add("2")
        self.m.take_next_task(self.ana.id)
        self.m.complete_task(t1.id)
        self.m.delete_task(t1.id)
        self.m.delete_task(t2.id)
        self.assertEqual(self.m.tasks, [])
        self.assertTrue(self.m.pending.is_empty())
        self.assertTrue(self.m.completed.is_empty())

    def test_delete_project_cascades(self):
        self.add(), self.add()
        self.assertEqual(self.m.delete_project(self.p.id), 2)
        self.assertEqual(self.m.tasks, [])
        self.assertEqual(self.m.projects, [])

    def test_reassign_and_return_to_queue(self):
        t = self.add()
        self.m.take_next_task(self.ana.id)
        self.m.reassign_task(t.id, self.bob.id)
        self.assertEqual(t.assignee_id, self.bob.id)
        self.m.return_to_queue(t.id)
        self.assertEqual(t.status, STATUS_PENDING)
        self.assertEqual(self.m.pending_tasks(), [t])

    def test_edit_task_is_atomic(self):
        t = self.add("Старо", 2, 5)
        with self.assertRaises(TaskManagerError):
            self.m.edit_task(t.id, title="Ново", priority=99)
        self.assertEqual(t.title, "Старо")
        self.m.edit_task(t.id, title="Ново", priority=4, deadline=_days(3))
        self.assertEqual((t.title, t.priority, t.deadline), ("Ново", 4, _days(3)))
        self.m.edit_task(t.id, clear_deadline=True)
        self.assertIsNone(t.deadline)

    def test_search(self):
        a = self.m.add_task("Обучение на модел", self.p.id, description="GPU клъстер")
        self.m.add_task("Документация", self.p.id)
        self.assertEqual(self.m.search_tasks("МОДЕЛ"), [a])
        self.assertEqual(self.m.search_tasks("gpu"), [a])
        self.assertIs(self.m.get_task(a.id), a)
        with self.assertRaises(TaskManagerError):
            self.m.get_task(999)
        self.assertIs(self.m.find_member_by_name("борис"), self.bob)
        self.assertIsNone(self.m.find_member_by_name("Никой"))

    def test_filter_overdue(self):
        late = self.add(deadline=_days(-3))
        self.add(deadline=_days(3))
        self.assertEqual(self.m.filter_tasks(overdue_only=True), [late])

    def test_sort_tasks(self):
        tasks = [self.add("в", 1, 3), self.add("а", 4, 9), self.add("б", 3, 1)]
        for algorithm in ("quick", "merge"):
            by_prio, _ = self.m.sort_tasks(tasks, "priority", algorithm)
            self.assertEqual([t.title for t in by_prio], ["а", "б", "в"])
            by_hours, _ = self.m.sort_tasks(tasks, "estimate", algorithm)
            self.assertEqual([t.estimate_hours for t in by_hours], [1, 3, 9])
            by_title, _ = self.m.sort_tasks(tasks, "title", algorithm)
            self.assertEqual([t.title for t in by_title], ["а", "б", "в"])


class AnalyticsTests(unittest.TestCase):
    def test_loads_and_levels(self):
        m = TaskManager()
        p = m.add_project("П")
        ana = m.add_member("Ана", "ML инженер", 10)
        m.add_member("Борис", "ML инженер", 40)
        m.add_task("x", p.id, 4, 12)
        m.take_next_task(ana.id)
        loads = analytics.member_loads(m)
        self.assertEqual(loads[0].member.name, "Ана")  # най-натовареният е първи
        self.assertAlmostEqual(loads[0].utilization, 1.2)
        self.assertEqual(loads[0].level, "Претоварен")
        self.assertEqual(loads[1].level, "Свободен")
        tips = analytics.recommendations(m, loads)
        self.assertTrue(any("Преместете задача" in tip and "Борис" in tip for tip in tips))

    def test_project_progress_and_risk(self):
        m = TaskManager()
        p = m.add_project("П", deadline=_days(-1))
        member = m.add_member("Ана", "ML инженер")
        t = m.add_task("x", p.id, 2, 10)
        m.add_task("y", p.id, 2, 30)
        m.take_next_task(member.id)
        m.complete_task(t.id)
        progress = analytics.project_progress(m)[0]
        self.assertEqual((progress.done, progress.total), (1, 2))
        self.assertAlmostEqual(progress.percent, 0.25)
        self.assertEqual(progress.risk, "Просрочен")

    def test_empty_system(self):
        m = TaskManager()
        self.assertEqual(analytics.member_loads(m), [])
        self.assertIn("ОТЧЕТ", analytics.build_text_report(m))

    def test_demo_report(self):
        report = analytics.build_text_report(create_demo_manager())
        self.assertIn("Претоварен", report)
        self.assertIn("Преместете задача", report)


class StorageTests(unittest.TestCase):
    def test_round_trip_preserves_queue_and_stack(self):
        m = create_demo_manager()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            storage.save(m, path)
            loaded, _ = storage.load(path)
        self.assertEqual(loaded.to_dict(), m.to_dict())
        self.assertEqual([t.id for t in loaded.pending], [t.id for t in m.pending])
        self.assertEqual([t.id for t in loaded.completed], [t.id for t in m.completed])
        # новите ID-та продължават коректно
        new = loaded.add_task("нова", loaded.projects[0].id)
        self.assertEqual(new.id, max(t.id for t in m.tasks) + 1)

    def test_missing_and_corrupt_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            m, message = storage.load(path)
            self.assertTrue(m.tasks)
            self.assertIn("демонстрационни", message)
            path.write_text("{ това не е JSON", encoding="utf-8")
            m, message = storage.load(path)
            self.assertIn("повреден", message)
            self.assertTrue(m.tasks)
            self.assertTrue(any("повреден" in p.name for p in Path(tmp).iterdir()))

    def test_inconsistent_data_is_repaired(self):
        m = create_demo_manager()
        data = m.to_dict()
        data["pending_queue"] = []                        # "забравена" опашка
        data["tasks"][0]["status"] = STATUS_IN_PROGRESS    # задача без валиден изпълнител
        data["tasks"][0]["assignee_id"] = 999
        repaired = TaskManager.from_dict(data)
        pending_ids = [t.id for t in repaired.pending]
        expected = [t["id"] for t in data["tasks"] if t["status"] == STATUS_PENDING]
        self.assertEqual(sorted(pending_ids), sorted(expected + [data["tasks"][0]["id"]]))


if __name__ == "__main__":
    unittest.main()
