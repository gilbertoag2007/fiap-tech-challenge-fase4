"""Renderiza docs/relatorio-tecnico-fase4.md em PDF A4 com ReportLab.

Executar da raiz: python3 scripts/gerar_relatorio_pdf.py
Requer reportlab; para acentos, usa Arial ou DejaVu Sans se disponíveis.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, KeepTogether, PageTemplate, Paragraph,
    Preformatted, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/relatorio-tecnico-fase4.md'
TARGET = ROOT / 'docs/relatorio-tecnico-fase4.pdf'
PAGE_W, PAGE_H = A4
LEFT = RIGHT = 50
TOP = 52
BOTTOM = 50
WIDTH = PAGE_W - LEFT - RIGHT
INK = colors.HexColor('#193047')
TEAL = colors.HexColor('#087e8b')
PALE = colors.HexColor('#eaf3f5')
LINE = colors.HexColor('#d7e2e6')


def register_fonts():
    choices = [
        ('Arial', '/System/Library/Fonts/Supplemental/Arial.ttf', '/System/Library/Fonts/Supplemental/Arial Bold.ttf'),
        ('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
    ]
    for family, regular, bold in choices:
        if Path(regular).exists() and Path(bold).exists():
            pdfmetrics.registerFont(TTFont(family, regular))
            pdfmetrics.registerFont(TTFont(family + '-Bold', bold))
            pdfmetrics.registerFontFamily(family, normal=family, bold=family + '-Bold')
            return family, family + '-Bold'
    return 'Helvetica', 'Helvetica-Bold'


REGULAR, BOLD = register_fonts()
styles = getSampleStyleSheet()
STYLE = {
    'title': ParagraphStyle('FiapTitle', fontName=BOLD, fontSize=23, leading=27, textColor=INK, spaceAfter=10),
    'h1': ParagraphStyle('FiapH1', fontName=BOLD, fontSize=14, leading=18, textColor=TEAL, spaceBefore=17, spaceAfter=7, keepWithNext=True),
    'h2': ParagraphStyle('FiapH2', fontName=BOLD, fontSize=10.5, leading=14, textColor=INK, spaceBefore=12, spaceAfter=5, keepWithNext=True),
    'body': ParagraphStyle('FiapBody', fontName=REGULAR, fontSize=9.2, leading=13.4, textColor=INK, spaceAfter=8, splitLongWords=True),
    'bullet': ParagraphStyle('FiapBullet', fontName=REGULAR, fontSize=9.2, leading=13.4, textColor=INK, leftIndent=15, firstLineIndent=-9, spaceAfter=5),
    'table': ParagraphStyle('FiapTable', fontName=REGULAR, fontSize=7.3, leading=10.1, textColor=INK, splitLongWords=True),
    'tablehead': ParagraphStyle('FiapTableHead', fontName=BOLD, fontSize=7.3, leading=10.1, textColor=colors.white, splitLongWords=True),
    'caption': ParagraphStyle('FiapCaption', fontName=REGULAR, fontSize=8.2, leading=11, textColor=INK, alignment=TA_CENTER, spaceBefore=4, spaceAfter=10),
    'code': ParagraphStyle('FiapCode', fontName='Courier', fontSize=7.8, leading=10, textColor=INK, backColor=PALE, leftIndent=7, rightIndent=7, spaceBefore=4, spaceAfter=10),
}
TOKEN = re.compile(r'(\[([^]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*|`([^`]+)`)')


def inline(value: str) -> str:
    parts = []
    pos = 0
    for match in TOKEN.finditer(value):
        parts.append(html.escape(value[pos:match.start()]))
        if match.group(2) is not None:
            label = html.escape(match.group(2))
            target = html.escape(match.group(3), quote=True)
            parts.append(f'<link href="{target}" color="#087e8b">{label}</link>')
        elif match.group(4) is not None:
            parts.append('<b>' + html.escape(match.group(4)) + '</b>')
        else:
            parts.append('<font color="#075f69">' + html.escape(match.group(5)) + '</font>')
        pos = match.end()
    parts.append(html.escape(value[pos:]))
    return ''.join(parts).replace('  \n', '<br/>')


def table_from(lines):
    rows = []
    for line in lines:
        vals = [v.strip() for v in line.strip().strip('|').split('|')]
        if all(re.fullmatch(r':?-+:?', v) for v in vals):
            continue
        rows.append(vals)
    cols = max(map(len, rows))
    if cols == 3:
        widths = [WIDTH * .38, WIDTH * .42, WIDTH * .20]
    elif cols == 2:
        widths = [WIDTH * .31, WIDTH * .69]
    elif cols == 6:
        widths = [WIDTH * .27] + [WIDTH * .146] * 5
    else:
        widths = [WIDTH / cols] * cols
    matrix = []
    for index, row in enumerate(rows):
        style = STYLE['tablehead' if index == 0 else 'table']
        matrix.append([Paragraph(inline(v), style) for v in row] + [''] * (cols - len(row)))
    result = Table(matrix, colWidths=widths, repeatRows=1, hAlign='LEFT')
    result.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TEAL),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, PALE]),
        ('GRID', (0, 0), (-1, -1), .25, LINE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return result


def parse():
    lines = SOURCE.read_text(encoding='utf-8').splitlines()
    story = []
    paragraph = []

    def flush():
        if paragraph:
            story.append(Paragraph(inline(' '.join(paragraph)), STYLE['body']))
            paragraph.clear()

    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            flush()
            i += 1
            continue
        if line.startswith('```'):
            flush()
            i += 1
            code = []
            while i < len(lines) and not lines[i].startswith('```'):
                code.append(lines[i])
                i += 1
            story.append(Preformatted('\n'.join(code), STYLE['code'], maxLineLength=92, splitChars=' /'))
            i += 1
            continue
        if line.startswith('|'):
            flush()
            group = []
            while i < len(lines) and lines[i].startswith('|'):
                group.append(lines[i]); i += 1
            story += [table_from(group), Spacer(1, 11)]
            continue
        pic = re.fullmatch(r'!\[([^]]+)\]\(([^)]+)\)', line)
        if pic:
            flush()
            path = SOURCE.parent / pic.group(2)
            img = ImageReader(str(path))
            w, h = img.getSize()
            size = min(WIDTH * .94 / w, (PAGE_H - TOP - BOTTOM - 75) / h)
            picture = Image(str(path), width=w * size, height=h * size, hAlign='CENTER')
            story.append(KeepTogether([picture, Paragraph(html.escape(pic.group(1)), STYLE['caption'])]))
            i += 1
            continue
        if line.startswith('# '):
            flush(); story.append(Paragraph(inline(line[2:]), STYLE['title']))
        elif line.startswith('## '):
            flush(); story.append(Paragraph(inline(line[3:]), STYLE['h1']))
        elif line.startswith('### '):
            flush(); story.append(Paragraph(inline(line[4:]), STYLE['h2']))
        elif line.startswith('- ') or re.match(r'^\d+\. ', line):
            flush()
            content = line[2:] if line.startswith('- ') else re.sub(r'^\d+\. ', '', line)
            marker = '•' if line.startswith('- ') else line.split('.')[0] + '.'
            story.append(KeepTogether([Paragraph(html.escape(marker) + ' ' + inline(content), STYLE['bullet'])]))
        else:
            paragraph.append(line.rstrip())
        i += 1
    flush()
    return story


class Report(BaseDocTemplate):
    def __init__(self):
        super().__init__(str(TARGET), pagesize=A4, leftMargin=LEFT, rightMargin=RIGHT,
                         topMargin=TOP, bottomMargin=BOTTOM, title='Relatório técnico - Prontuário Digital',
                         author='Projeto FIAP Tech Challenge')
        frame = Frame(LEFT, BOTTOM, WIDTH, PAGE_H - TOP - BOTTOM, leftPadding=0,
                      bottomPadding=0, rightPadding=0, topPadding=0)
        self.addPageTemplates(PageTemplate(id='content', frames=frame, onPage=self.decorate))

    def decorate(self, canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.line(LEFT, PAGE_H - 35, PAGE_W - RIGHT, PAGE_H - 35)
        canvas.setFont(REGULAR, 7.3)
        canvas.setFillColor(TEAL)
        canvas.drawString(LEFT, PAGE_H - 28, 'FIAP · TECH CHALLENGE FASE 4')
        canvas.setFillColor(INK)
        canvas.drawString(LEFT, 28, 'Prontuário Digital · relatório técnico · 11/11/2026')
        canvas.drawRightString(PAGE_W - RIGHT, 28, str(doc.page))
        canvas.restoreState()


def main():
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    Report().build(parse())
    print(TARGET)


if __name__ == '__main__':
    main()
