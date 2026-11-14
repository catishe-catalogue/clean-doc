from app.services.converter_service import BreakType, _classify_break
from app.workers.tasks import _classify_break as tasks_classify_break


def test_classify_break_cases() -> None:
    """Проверка 5 ключевых сценариев классификации переносов строк: Enter (hard) vs Shift+Enter (soft)."""
    # 1. Перенос строки внутри логического предложения без терминальной пунктуации -> soft break
    assert (
        _classify_break(
            "Мы ищем аналитика, который",
            "поможет развивать продукт:",
        )
        == BreakType.SOFT.value
    )

    # 2. Перенос строки с дефисом на конце слова -> soft break
    assert (
        _classify_break(
            "описание бизнес-процессов As Is / To Be, построение BPMN-",
            "схем;",
        )
        == BreakType.SOFT.value
    )

    # 3. Предыдущая строка оканчивается точкой, восклицательным или вопросительным знаком -> hard break
    assert (
        _classify_break(
            "Автоматическое удаление файлов через 2 часа.",
            "Наш стек: FastAPI, Next.js, Docker.",
        )
        == BreakType.HARD.value
    )

    # 4. Предыдущая строка оканчивается двоеточием (ввод нового блока/секции) -> hard break
    assert (
        _classify_break(
            "Обязанности:",
            "сбор, анализ и формализация требований",
        )
        == BreakType.HARD.value
    )

    # 5. Следующая строка начинается с маркера маркированного или нумерованного списка -> hard break
    assert (
        _classify_break(
            "Требования к кандидату",
            "• опыт работы аналитиком от 3 лет",
        )
        == BreakType.HARD.value
    )
    assert (
        _classify_break(
            "Этапы согласования",
            "1. Подписание соглашения",
        )
        == BreakType.HARD.value
    )

    # Дополнительно: пустые строки классифицируются как hard break
    assert _classify_break("", "Текст") == BreakType.HARD.value
    assert _classify_break("Текст", "") == BreakType.HARD.value

    # Проверка, что tasks реэкспортирует _classify_break идентично
    assert tasks_classify_break("Заголовок:", "Строка") == BreakType.HARD.value
