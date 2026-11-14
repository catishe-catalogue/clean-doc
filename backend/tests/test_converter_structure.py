import os
import tempfile
from pathlib import Path

import docx

from app.workers.tasks import _run_docling

MOCK_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "mock_data"


def test_vacancy_analyst_docx_structure() -> None:
    """
    Сквозной интеграционный тест структурной конвертации эталонного PDF вакансии в DOCX.
    Проверяет сохранение иерархии заголовков, стилей списков, начертания bold и детокенизацию.
    """
    # Предпочитаем файл «test-data-vacancy.pdf», при отсутствии fallback на test-data-resume.pdf
    pdf_path = MOCK_DATA_DIR / "test-data-vacancy.pdf"
    if not pdf_path.exists():
        pdf_path = MOCK_DATA_DIR / "test-data-resume.pdf"

    assert pdf_path.exists(), f"Файл эталона {pdf_path} не найден в mock_data/"

    with tempfile.TemporaryDirectory(prefix="cleandoc_struct_test_") as tmpdir:
        output_docx = os.path.join(tmpdir, "output.docx")
        _run_docling("docx", str(pdf_path), output_docx)

        assert os.path.exists(output_docx)
        doc = docx.Document(output_docx)
        paragraphs = list(doc.paragraphs)

        # 1. H1 (heading 1) == «Аналитик» — ровно один во всем документе
        h1_indices = [
            i for i, p in enumerate(paragraphs) if p.style.name.lower() in ("heading 1", "title")
        ]
        assert len(h1_indices) == 1, f"Ожидался ровно один заголовок H1, получено {len(h1_indices)}"
        h1_idx = h1_indices[0]
        assert paragraphs[h1_idx].text.strip() == "Аналитик"

        # 2. Первый параграф после H1 — «Занятость: полная» (не слит с H1)
        first_p_after_h1 = paragraphs[h1_idx + 1]
        assert first_p_after_h1.text.strip() == "Занятость: полная"
        assert "Аналитик" not in first_p_after_h1.text

        # 3. Параграф «Формат работы...» содержит '/', ':' и не содержит '\n'
        format_p = [p for p in paragraphs if "Формат работы" in p.text]
        assert len(format_p) == 1, "Параграф с форматом работы не найден"
        assert "/" in format_p[0].text, "Символ '/' потерян в формате работы"
        assert ":" in format_p[0].text, "Символ ':' потерян в формате работы"
        assert "\n" not in format_p[0].text, (
            "Внутри параграфа обнаружен некорректный символ перевода строки"
        )

        # 4. Параграф «З/п...» содержит '/'
        salary_p = [p for p in paragraphs if "З/п" in p.text or "З п" in p.text]
        assert len(salary_p) == 1, "Параграф заработной платы не найден"
        assert "З/п" in salary_p[0].text, "Символ '/' в аббревиатуре 'З/п' потерян"
        assert "/" in salary_p[0].text

        # 5. В документе >= 4 параграфов со стилем List Bullet
        bullet_paragraphs = [p for p in paragraphs if p.style.name == "List Bullet"]
        assert len(bullet_paragraphs) >= 4, (
            f"Ожидалось не менее 4 параграфов List Bullet, найдено {len(bullet_paragraphs)}"
        )

        # 6. Параграфы разделов («Обязанности», «Требования», «Личные качества», «Условия»)
        # имеют style.name == 'Heading 2' и все runs в них bold=True
        section_titles = ["Обязанности", "Требования", "Личные качества", "Условия"]
        for title in section_titles:
            sec_p = [p for p in paragraphs if p.text.strip().rstrip(":").startswith(title)]
            assert len(sec_p) == 1, f"Секция {title} не найдена или дублируется"
            assert sec_p[0].style.name == "Heading 2", (
                f"Секция {title} имеет стиль {sec_p[0].style.name}, ожидался Heading 2"
            )
            assert len(sec_p[0].runs) > 0, f"Секция {title} не содержит runs"
            assert all(run.bold for run in sec_p[0].runs), (
                f"Не все runs в заголовке {title} имеют bold=True: {[r.bold for r in sec_p[0].runs]}"
            )

        # 7. Нет параграфов, где p.text.strip() == '' (кроме 0-2 пустых между секциями)
        empty_paragraphs = [p for p in paragraphs if not p.text.strip()]
        assert len(empty_paragraphs) <= 2, (
            f"Слишком много пустых абзацев ({len(empty_paragraphs)}), ожидалось не более 2"
        )

        # 8. Нет параграфов с p.text.strip().startswith(':') кроме случаев списков
        colon_paragraphs = [
            p
            for p in paragraphs
            if p.text.strip().startswith(":") and p.style.name != "List Bullet"
        ]
        assert len(colon_paragraphs) == 0, (
            f"Обнаружены параграфы, начинающиеся с двоеточия: {colon_paragraphs}"
        )
