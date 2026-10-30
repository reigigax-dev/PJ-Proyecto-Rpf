from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

SEX_LABEL = {True: "F", False: "M"}

COLUMNS = [
    ("ID", 7),
    ("RUT", 14),
    ("Nombres", 26),
    ("Apellidos", 26),
    ("Sexo", 7),
    ("Fecha de nacimiento", 20),
    ("Lugar de nacimiento", 22),
    ("N° documento", 15),
    ("Foto frontal", 16),
    ("Foto trasera", 16),
]

def format_rut(rut):
    if not rut or len(rut) < 2:
        return rut or ""
    body, vd = rut[:-1], rut[-1]
    return f"{int(body):,}".replace(",", ".") + f"-{vd}" if body.isdigit() else rut

def build_workbook(records, image_url=None):
    wb = Workbook()
    ws = wb.active
    ws.title = "Registos"

    header_fill = PatternFill("solid", fgColor="1F4E78")
    for col, (title, width) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=col, value=title)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[get_column_letter(col)].width = width

    row = 1
    for r in records:
        row += 1
        values = [
            r.id,
            format_rut(r.document),
            r.first_names,
            r.last_names,
            SEX_LABEL.get(r.sex, ""),
            r.born_date,
            r.born_location or "",
            r.document_number,
        ]
        for col, value in enumerate(values, start=1):
            ws.cell(row=row, column=col, value=value)
        ws.cell(row=row, column=6).number_format = "DD-MM-YYYY"
        ws.cell(row=row, column=8).number_format = "0"

        for col, field in ((9, r.document_front_picture), (10, r.document_back_picture)):
            url = image_url(field) if (image_url and field) else None
            if url:
                cell = ws.cell(row=row, column=col, value="Ver foto")
                cell.hyperlink = url
                cell.font = Font(color="0563C1", underline="single")

        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}{max(row, 1)}"

        buffer = BytesIO()
        wb.save(buffer)
        return buffer.getvalue()