"""Excel (openpyxl) and PDF (reportlab) export of a report table."""
import io

from django.http import HttpResponse
from django.utils import timezone

from apps.accounts.models import SystemSetting


def _filename(slug, ext):
    return f'{slug}-{timezone.localdate():%Y%m%d}.{ext}'


def to_excel(slug, title, columns, rows, summary):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = title[:31]
    ws.append([SystemSetting.load().institution_name])
    ws.append([title])
    ws.append([f'Generated {timezone.localtime():%d %b %Y %H:%M}'])
    ws['A1'].font = Font(bold=True, size=13)
    ws['A2'].font = Font(bold=True, size=12)
    ws.append([])
    header_row = ws.max_row + 1
    ws.append(columns)
    for cell in ws[header_row]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor='1F4E79')
        cell.alignment = Alignment(vertical='center')
    for row in rows:
        ws.append(list(row))
    ws.freeze_panes = ws.cell(row=header_row + 1, column=1)
    for i, col in enumerate(columns, start=1):
        width = max([len(str(col))] + [len(str(r[i - 1])) for r in rows[:500]]) + 2
        ws.column_dimensions[get_column_letter(i)].width = min(width, 45)
    if summary:
        sheet = wb.create_sheet('Summary')
        sheet.append(['Measure', 'Value'])
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for k, v in summary.items():
            sheet.append([k, v])
        sheet.column_dimensions['A'].width = 34
        sheet.column_dimensions['B'].width = 16
    buf = io.BytesIO()
    wb.save(buf)
    response = HttpResponse(buf.getvalue(),
                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{_filename(slug, "xlsx")}"'
    return response


def to_pdf(slug, title, columns, rows, summary):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=1.2 * cm, rightMargin=1.2 * cm,
                            topMargin=1.2 * cm, bottomMargin=1.2 * cm, title=title)
    styles = getSampleStyleSheet()
    cell = styles['BodyText'].clone('cell', fontSize=8, leading=10)
    head = styles['BodyText'].clone('head', fontSize=8, leading=10, textColor=colors.white, fontName='Helvetica-Bold')
    story = [Paragraph(SystemSetting.load().institution_name, styles['Title']),
             Paragraph(title, styles['Heading2']),
             Paragraph(f'Generated {timezone.localtime():%d %b %Y %H:%M}', styles['Normal']),
             Spacer(1, 0.4 * cm)]
    if summary:
        t = Table([[k, str(v)] for k, v in summary.items()], hAlign='LEFT', colWidths=[7 * cm, 3 * cm])
        t.setStyle(TableStyle([('FONTSIZE', (0, 0), (-1, -1), 9), ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                               ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#EEF3F8'))]))
        story += [t, Spacer(1, 0.5 * cm)]
    data = [[Paragraph(str(c), head) for c in columns]]
    data += [[Paragraph(str(v), cell) for v in r] for r in rows] or [[Paragraph('No records.', cell)] +
                                                                   [''] * (len(columns) - 1)]
    width = landscape(A4)[0] - 2.4 * cm
    table = Table(data, repeatRows=1, colWidths=[width / len(columns)] * len(columns))
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F7FA')]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(table)
    doc.build(story)
    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{_filename(slug, "pdf")}"'
    return response
