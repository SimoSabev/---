"""Демонстрационни данни – реалистичен AI екип с няколко проекта.

Сроковете се изчисляват спрямо днешната дата, така че демонстрацията
изглежда еднакво независимо кога се стартира програмата.
"""

from __future__ import annotations

from datetime import date, timedelta

from .manager import TaskManager


def _in_days(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def create_demo_manager() -> TaskManager:
    m = TaskManager()

    chatbot = m.add_project("LLM чатбот за клиенти",
                            "Асистент за поддръжка с RAG върху базата знания", _in_days(21))
    recsys = m.add_project("Система за препоръки",
                           "Персонализирани препоръки на продукти", _in_days(35))
    vision = m.add_project("Компютърно зрение – QA",
                           "Откриване на дефекти в продукцията по снимки", _in_days(5))
    mlops = m.add_project("MLOps платформа",
                          "CI/CD за модели, мониторинг и регистър на модели", _in_days(50))

    ivan = m.add_member("Иван Петров", "ML инженер", 40)
    maria = m.add_member("Мария Георгиева", "Data инженер", 40)
    georgi = m.add_member("Георги Димитров", "MLOps инженер", 32)
    elena = m.add_member("Елена Николова", "AI изследовател", 40)
    petar = m.add_member("Петър Стоянов", "Backend разработчик", 40)
    desi = m.add_member("Десислава Иванова", "QA / оценка на модели", 24)

    # (заглавие, проект, приоритет, часове, срок след N дни, роля, изпълнител, приключена?)
    started = [
        ("Събиране и почистване на FAQ данни", chatbot, 3, 12, -6, "Data инженер", maria, True),
        ("Избор на embedding модел", chatbot, 3, 8, -4, "AI изследовател", elena, True),
        ("Векторна база данни (RAG индекс)", chatbot, 4, 16, 3, "Data инженер", maria, False),
        ("Fine-tuning на LLM върху диалози", chatbot, 4, 20, 10, "ML инженер", ivan, False),
        ("REST API за чатбота", chatbot, 3, 14, 12, "Backend разработчик", petar, False),
        ("Анотиране на снимки с дефекти", vision, 4, 10, -2, "Data инженер", maria, True),
        ("Обучение на YOLO модел", vision, 4, 20, -1, "ML инженер", ivan, False),
        ("Аугментация на данните", vision, 2, 8, 4, None, ivan, False),
        ("Метрики precision/recall за модела", vision, 3, 8, 5, "QA / оценка на модели", desi, False),
        ("Feature store за потребители", recsys, 3, 18, 20, "Data инженер", maria, False),
        ("Базов модел – collaborative filtering", recsys, 3, 16, 25, "AI изследовател", elena, True),
        ("Docker образи за inference", mlops, 3, 10, 15, "MLOps инженер", georgi, False),
    ]
    for title, project, prio, hours, days, role, member, done in started:
        task = m.add_task(title, project.id, prio, hours, _in_days(days), required_role=role)
        m.take_next_task(member.id)
        if done:
            m.complete_task(task.id)

    # Чакащи задачи – нарочно не са подредени по приоритет, за да се демонстрира
    # пренареждането на опашката с Quick/Merge Sort.
    pending = [
        ("Документация на API", chatbot, 1, 6, 18, "Backend разработчик"),
        ("Оценка на халюцинации на LLM", chatbot, 4, 10, 8, "QA / оценка на модели"),
        ("A/B тест на препоръките", recsys, 2, 12, 30, "AI изследовател"),
        ("Мониторинг на data drift", mlops, 3, 14, 28, "MLOps инженер"),
        ("Регистър на модели (MLflow)", mlops, 2, 8, 40, "MLOps инженер"),
        ("Защита от prompt injection", chatbot, 4, 8, 9, "Backend разработчик"),
        ("Дашборд за бизнес метрики", recsys, 1, 10, 33, "Backend разработчик"),
        ("Оптимизация на латентността", vision, 3, 6, 5, "ML инженер"),
    ]
    for title, project, prio, hours, days, role in pending:
        m.add_task(title, project.id, prio, hours, _in_days(days), required_role=role)

    return m
