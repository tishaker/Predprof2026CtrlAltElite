# pdf_utils.py
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
import os


def register_russian_fonts():
    """Регистрирует русские шрифты"""
    # Пытаемся найти шрифты в разных местах
    font_paths = [
        'arial.ttf',  # Windows
        '/usr/share/fonts/truetype/msttcorefonts/arial.ttf',  # Linux
        '/Library/Fonts/Arial.ttf',  # Mac
        'DejaVuSans.ttf',  # Linux alternative
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('RussianFont', font_path))
                pdfmetrics.registerFont(TTFont('RussianFont-Bold', font_path))
                return 'RussianFont'
            except:
                pass

    # Если не нашли шрифты, создаем простой PDF с английскими символами
    return 'Helvetica'


def create_pdf_report(report_type, program='all', date='all', applicants_data=None):
    """Создает PDF отчет"""
    buffer = io.BytesIO()

    # Регистрируем шрифты
    font_name = register_russian_fonts()

    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    # Базовые стили
    styles = getSampleStyleSheet()

    # Создаем стили с русскими шрифтами
    if font_name != 'Helvetica':
        # Создаем новые стили с русскими шрифтами
        title_style = ParagraphStyle(
            'RussianTitle',
            fontName=f'{font_name}-Bold',
            fontSize=16,
            alignment=1,
            spaceAfter=30
        )

        normal_style = ParagraphStyle(
            'RussianNormal',
            fontName=font_name,
            fontSize=10
        )
    else:
        # Используем стандартные стили для английского
        title_style = styles['Heading1']
        normal_style = styles['Normal']

    # Добавляем заголовок
    if report_type == 'summary':
        title = "Summary Report" if font_name == 'Helvetica' else "Сводный отчет"
    elif report_type == 'detailed':
        title = "Detailed List" if font_name == 'Helvetica' else "Детальный список"
    else:
        title = "Competition Lists" if font_name == 'Helvetica' else "Конкурсные списки"

    elements.append(Paragraph(title, title_style))

    # Добавляем таблицу (пример)
    if applicants_data:
        table_data = [['ID', 'Score', 'Consent']]
        for app in applicants_data:
            table_data.append([
                str(app['id']),
                str(app['score']),
                'Yes' if app['consent'] else 'No'
            ])

        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))

        elements.append(table)

    # Добавляем дату
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))

    doc.build(elements)
    buffer.seek(0)

    return buffer