"""Build the Excel report from the same frames used by the HTML and CSV."""
import json

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from .thresholds import ACTIONS, LEVELS

def add_table(book, title, headers, rows):
    sheet = book.create_sheet(title)
    sheet.append(list(headers))
    widths = [len(str(header)) + 3 for header in headers]
    for row in rows:
        values = [None if pd.isna(value) else value for value in row]
        sheet.append(values)
        for index, value in enumerate(values, start=1):
            cell = sheet.cell(sheet.max_row, index)
            if isinstance(value, str):
                cell.data_type = "s"
                widths[index - 1] = max(widths[index - 1], min(len(value) + 3, 58))
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = max(12, min(width, 58))
    for cell in sheet[1]:
        cell.font = Font(color="FFFFFF", bold=True)
        cell.fill = PatternFill("solid", fgColor="123646")
        cell.alignment = Alignment(vertical="center")
    sheet.row_dimensions[1].height = 26
    sheet.freeze_panes = "A2"
    sheet.sheet_view.showGridLines = False
    if sheet.max_row > 1:
        table = Table(displayName="T_" + title, ref=sheet.dimensions)
        table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
        sheet.add_table(table)
    return sheet

def format_columns(sheet, names, pattern):
    for cell in sheet[1]:
        if cell.value in names:
            for (value,) in sheet.iter_rows(min_row=2, min_col=cell.column, max_col=cell.column):
                value.number_format = pattern

def write_workbook(out, reference, summary):
    book = Workbook()
    book.remove(book.active)
    book.properties.title = f"Sông Hồng EWS · {summary['snapshot_month']}"
    counts = summary["snapshot_alerts"]
    total = summary["snapshot_total"]
    overview = add_table(book, "00_Overview", ["Mức", "Khoản vay", "Tỷ trọng", "Hành động"], [
        (level, counts.get(level, 0), counts.get(level, 0) / total, ACTIONS[level])
        for level in [*LEVELS, "Existing 30+"]
    ])
    format_columns(overview, {"Tỷ trọng"}, "0.00%")
    overview["A9"] = "Tháng đánh giá"
    overview["B9"] = summary["snapshot_month"]
    overview["A10"] = "Tổng danh mục"
    overview["B10"] = total
    overview["A11"] = "Mã lượt mô hình"
    overview["B11"] = summary["run_id"]
    overview["A12"] = "Số dòng tối đa mỗi mức trong 05_EWS_Alerts"
    overview["B12"] = 80
    chart = BarChart()
    chart.title = "Phân bổ danh mục"
    chart.add_data(Reference(overview, min_col=2, min_row=1, max_row=6), titles_from_data=True)
    chart.set_categories(Reference(overview, min_col=1, min_row=2, max_row=6))
    overview.add_chart(chart, "F2")
    payload = json.loads((out / "excel_snapshot.json").read_text(encoding="utf-8"))
    for title, key in [("01_Raw_AsOf", "raw"), ("02_Profile", "profiles"),
                       ("03_Features", "features"), ("05_EWS_Alerts", "alerts")]:
        data = payload[key]
        sheet = add_table(book, title, data["columns"], data["data"])
        format_columns(sheet, {"pd_3m"}, "0.0000%")
    for title, filename in [
        ("04_Thresholds", "thresholds"), ("06_Source_Inventory", "source_inventory"),
        ("07_Backtesting", "backtest_monthly"), ("08_Validation_30", "comparison_30"),
        ("09_Validation_90", "comparison_90"), ("10_Missing", "missing_profile"),
        ("11_Outliers", "outliers_profile"), ("12_Income_Drift", "income_drift"),
        ("13_Labels", "label_summary"), ("14_Calibration_30", "calibration_30"),
    ]:
        frame = pd.read_csv(reference / f"{filename}.csv", float_precision="round_trip")
        sheet = add_table(book, title, frame.columns, frame.itertuples(index=False, name=None))
        format_columns(sheet, {"lower_pd", "target_cumulative_share", "validation_cumulative_share",
                               "mean_pd", "event_rate", "observed_rate", "pct_missing",
                               "pct_missing_income"}, "0.00%")
    book.save(out / "EWS_Excel.xlsx")
