import logging
import os
import traceback
import io

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

from config import FONT_PATH_FOR_BOT_SESSION

logger = logging.getLogger(__name__)
HAS_DEJAVU_FONT = False

def register_font():
    """
    Регистрирует шрифт для использования в PDF.
    Эту функцию следует вызывать один раз при старте приложения.
    """
    global HAS_DEJAVU_FONT
    if FONT_PATH_FOR_BOT_SESSION and os.path.exists(FONT_PATH_FOR_BOT_SESSION):
        try:
            pdfmetrics.registerFont(TTFont('DejaVuSans', FONT_PATH_FOR_BOT_SESSION))
            HAS_DEJAVU_FONT = True
            logger.info(f"Шрифт {FONT_PATH_FOR_BOT_SESSION} зарегистрирован для PDF.")
        except Exception as e:
            logger.error(f"Ошибка при регистрации шрифта для PDF: {e}")
            HAS_DEJAVU_FONT = False
    else:
        path_info = FONT_PATH_FOR_BOT_SESSION if FONT_PATH_FOR_BOT_SESSION else "<<путь не указан в config.py>>"
        logger.warning(f"Файл шрифта для PDF не найден или не определён: '{path_info}'. Будет использован Helvetica.")
        HAS_DEJAVU_FONT = False

def create_character_sheet_pdf(character_data):
    """
    Создает PDF-файл с листом персонажа в буфере памяти.
    Возвращает объект io.BytesIO с PDF-данными или None в случае ошибки.
    """
    pdf_buffer = io.BytesIO()
    try:
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4,
                                rightMargin=40, leftMargin=40,
                                topMargin=40, bottomMargin=40)
        story = []

        styles = getSampleStyleSheet()
        font_name = 'DejaVuSans' if HAS_DEJAVU_FONT else 'Helvetica'
        font_name_bold = 'DejaVuSans' if HAS_DEJAVU_FONT else 'Helvetica-Bold'

        style_normal = ParagraphStyle('NormalCustom', parent=styles['Normal'], fontName=font_name, fontSize=10, leading=12, alignment=TA_JUSTIFY)
        style_h1 = ParagraphStyle('H1Custom', parent=styles['h1'], fontName=font_name_bold, fontSize=18, leading=22, alignment=TA_CENTER, spaceAfter=12)
        style_h2 = ParagraphStyle('H2Custom', parent=styles['h2'], fontName=font_name_bold, fontSize=12, leading=14, spaceBefore=10, spaceAfter=4, alignment=TA_LEFT)
        style_label = ParagraphStyle('LabelCustom', parent=style_normal, fontName=font_name_bold)

        story.append(Paragraph(character_data.get("name", "Безымянный Герой"), style_h1))
        story.append(Spacer(1, 6))

        info_data = [
            [Paragraph("Раса:", style_label), Paragraph(character_data.get("race", "-"), style_normal)],
            [Paragraph("Класс:", style_label), Paragraph(character_data.get("class", "-"), style_normal)],
            [Paragraph("Предыстория (Bkgd):", style_label), Paragraph(character_data.get("background_name", "-"), style_normal)],
            [Paragraph("Мировоззрение:", style_label), Paragraph(character_data.get("alignment", "-"), style_normal)],
        ]
        info_table = Table(info_data, colWidths=[120, None])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 3)
        ]))
        story.append(info_table)
        story.append(Spacer(1, 6))

        story.append(Paragraph("Характеристики:", style_h2))
        story.append(Paragraph(character_data.get("stats", "-"), style_normal))

        story.append(Paragraph("Инвентарь:", style_h2))
        story.append(Paragraph(character_data.get("inventory", "-"), style_normal))

        story.append(Paragraph("Предыстория:", style_h2))
        backstory_text_html = character_data.get("backstory_text", "-").replace('\n', '<br/>\n')
        story.append(Paragraph(backstory_text_html, style_normal))

        story.append(Paragraph("Черты Личности:", style_h2))
        traits_data = [
            [Paragraph("Черта Характера:", style_label), Paragraph(character_data.get("trait", "-"), style_normal)],
            [Paragraph("Идеал:", style_label), Paragraph(character_data.get("ideal", "-"), style_normal)],
            [Paragraph("Привязанность:", style_label), Paragraph(character_data.get("bond", "-"), style_normal)],
            [Paragraph("Слабость:", style_label), Paragraph(character_data.get("flaw", "-"), style_normal)],
        ]
        traits_table = Table(traits_data, colWidths=[120, None])
        traits_table.setStyle(TableStyle([
             ('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0),
             ('RIGHTPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 3)
        ]))
        story.append(traits_table)

        doc.build(story)
        logger.info(f"PDF успешно создан в памяти.")
        pdf_buffer.seek(0)
        return pdf_buffer
    except Exception as e:
        logger.error(f"Ошибка при создании PDF в памяти: {e}")
        logger.error(traceback.format_exc())
        return None
