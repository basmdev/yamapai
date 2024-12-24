import os
from datetime import datetime

import openpyxl
from openpyxl.utils import get_column_letter


def create_excel_report(data):
    """Создание отчета в формате Excel."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Данные"

    headers = data[0].keys()

    for col, header in enumerate(headers, start=1):
        ws.cell(row=1, column=col, value=header)

    for row, entry in enumerate(data, start=2):
        for col, header in enumerate(headers, start=1):
            ws.cell(row=row, column=col, value=entry[header])

    for col, header in enumerate(headers, start=1):
        column_width = max(len(str(entry.get(header, ""))) for entry in data) + 2
        ws.column_dimensions[get_column_letter(col)].width = column_width

    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)

    current_time = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    filename = os.path.join(reports_dir, f"report_{current_time}.xlsx")

    wb.save(filename)


# data = [
#     {
#         "name": "filial_name",
#         "mapurl": "url",
#         "zoom": "maszoom",
#         "screen": "screenshot",
#         "airesponse": "response",
#     },
#     {
#         "name": "filial_nme",
#         "mapurl": "ul",
#         "zoom": "mazoom",
#         "screen": "screshot",
#         "airesponse": "reponse",
#     },
# ]
