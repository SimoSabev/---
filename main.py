"""Входна точка: Система за управление на задачи на AI екип.

Стартиране:  python main.py
"""

import sys
import traceback

from task_manager import storage
from task_manager.ui import ConsoleUI


def _configure_console() -> None:
    """Гарантира правилно показване на кирилица във всички конзоли."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main() -> int:
    _configure_console()
    manager, message = storage.load()
    ui = ConsoleUI(manager)
    try:
        ui.run(message)
    except (KeyboardInterrupt, EOFError):
        ui.save()
        print("\n\n  Програмата е прекратена. Данните са записани.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # непредвидена грешка – показваме я, без конзолата да се затвори
        traceback.print_exc()
        input("\nВъзникна неочаквана грешка. Натиснете Enter за изход...")
        sys.exit(1)
