"""W2 – Tạo báo cáo Data Quality dạng Excel (theo mẫu Q02_Data_description.xlsx của cô) + file hồ sơ sạch.

Chạy từ thư mục gốc repo:   python -m ews.dq_report      (cần PYTHONPATH=src, hoặc: cd src && python -m ews.dq_report)
Đầu ra:
  outputs/W2_Customer_Profile_DQ.xlsx   báo cáo; các bảng tổng hợp là CÔNG THỨC Excel (COUNTIFS, PERCENTILE...) trên sheet Data_Profile
  data/interim/customer_profile_clean.csv   hồ sơ đã làm sạch + cờ chất lượng (cho W4/W5; không đẩy lên GitHub)
"""
import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L
from . import config as C
from . import clean_rules as cr

F = lambda **k: Font(name="Arial", size=k.pop("size", 10), **k)
YEL = PatternFill("solid", start_color="FFF2CC", end_color="FFF2CC")
BLUE = PatternFill("solid", start_color="2E75B6", end_color="2E75B6")
GREY = PatternFill("solid", start_color="F2F2F2", end_color="F2F2F2")
thin = Side(style="thin", color="BFBFBF"); BD = Border(left=thin, right=thin, top=thin, bottom=thin)
WRAP = Alignment(wrap_text=True, vertical="top")

DATA_COLS = ["app_id", "profile_source", "app_ym"] + cr.NUM_COLS + ["perf_class", "target"]
COL = {c: L(i + 1) for i, c in enumerate(DATA_COLS)}

TREAT = {  # hướng xử lý từng biến (đã chốt – xem docs/W2_HUONG_DAN.md)
    "loan_amount_mil": "Không thiếu, không ngoại lai. Giữ nguyên.",
    "age": "Ngoài [18, 75] là lỗi nhập liệu: kẹp về nhóm biên gần nhất [18, 75] + cờ f_age_invalid.",
    "income_mil": "Thiếu ~4,5%: giữ trống + cờ f_income_missing (nhóm thiếu rủi ro hơn hẳn). > 500 là ngoại lai: chặn trên (cap) ở 500 + cờ f_income_outlier. Có drift từ 07/2023.",
    "work_months": "Thiếu ~10,7%: giữ trống + cờ f_work_missing (nhóm thiếu rủi ro hơn hẳn). Không vi phạm (age−18)×12.",
    "dti_pct": "> 200% cực đoan nhưng có thể xảy ra: giữ nguyên giá trị thực tế + cờ f_dti_outlier.",
    "cic_hist_months": "Không cần xử lý riêng (binning/chuẩn hóa xử lý đuôi).",
    "num_lenders": "Không cần xử lý riêng.",
    "card_util_pct": "Thiếu ~30% = không có thẻ (có ý nghĩa nghiệp vụ): giữ trống + cờ f_card_missing. > 100% = vượt hạn mức: giữ giá trị + cờ f_card_over100.",
    "inq_6m": "Không cần xử lý riêng.",
    "dpd_cnt_6m": "Luôn ≤ dpd_cnt_12m (đã kiểm tra). Không cần xử lý.",
    "dpd_cnt_12m": "Không vượt số tháng có lịch sử CIC (đã kiểm tra). Không cần xử lý.",
    "deposit_avg_3m_mil": "Thiếu ~38% = chưa có tài khoản tiền gửi: giữ trống + cờ f_deposit_missing.",
}


def hdr(ws, row, labels, widths=None):
    for j, t in enumerate(labels):
        c = ws.cell(row=row, column=1 + j, value=t)
        c.font = F(bold=True, color="FFFFFF"); c.fill = BLUE; c.border = BD
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[row].height = 32


def put(ws, r, c, v, fmt=None, bold=False, fill=None, wrap=False):
    x = ws.cell(row=r, column=c, value=v); x.font = F(bold=bold); x.border = BD
    if fmt: x.number_format = fmt
    if fill: x.fill = fill
    if wrap: x.alignment = WRAP
    return x


def build(df: pd.DataFrame, path):
    n = len(df); last = n + 1
    R = lambda c: f"Data_Profile!${COL[c]}$2:${COL[c]}${last}"
    wb = Workbook(); wb.remove(wb.active)

    # ------------------------------------------------------------------ README
    ws = wb.create_sheet("README")
    ws["A1"] = "W2 – Data Quality của hồ sơ khách hàng (Behavioral EWS)"; ws["A1"].font = F(bold=True, size=14)
    lines = [
        ("Mục đích", "Mô tả chất lượng dữ liệu hồ sơ: số lượng thiếu, ngoại lai, drift; chốt quy tắc xử lý. Theo mẫu Q2b/Q2c trong Q02_Data_description.xlsx của cô."),
        ("Tập dữ liệu", f"{n:,} khoản vay có lịch sử trả nợ (có trong perf_monthly): hồ sơ từ dev_2023 (Approved) + oot_2024H1. Mỗi dòng 1 app_id."),
        ("Sheet Data_Profile", "Dữ liệu GỐC chép từ CSV (trắng = dữ liệu). perf_class, target chỉ dùng để PHÂN TÍCH (Q2c), không làm input mô hình."),
        ("Sheet Q2b_Missing_outliers", "Missing / min / P1 / trung vị / P99 / max / số > P99 / hướng xử lý. Toàn bộ là công thức Excel."),
        ("Sheet Q2c_Missing_bad_rate", "Bad rate nhóm thiếu so với danh mục (Good+Bad). Quy ước 1,5 × bad rate danh mục. Công thức Excel."),
        ("Sheet Outlier_Rules", "Ngưỡng (ô vàng, sửa được) và số vi phạm từng quy tắc R01–R08. Công thức Excel."),
        ("Sheet Drift_Income", "Số hồ sơ, % thiếu và trung vị thu nhập theo tháng nộp hồ sơ; biểu đồ đứt gãy 07/2023."),
        ("Sheet Quy_tac_xu_ly", "Danh sách quy tắc xử lý đã chốt + tên hàm trong clean_rules.py + danh sách biến bị loại (leakage)."),
        ("Màu ô", "Xanh dương = tiêu đề · Vàng = ô có thể sửa · Trắng = dữ liệu / công thức."),
    ]
    for i, (a, b) in enumerate(lines):
        r = 3 + i
        ws.cell(row=r, column=1, value=a).font = F(bold=True); c = ws.cell(row=r, column=2, value=b); c.font = F(); c.alignment = WRAP
    ws.column_dimensions["A"].width = 28; ws.column_dimensions["B"].width = 110

    # ------------------------------------------------------------------ Q2b
    ws = wb.create_sheet("Q2b_Missing_outliers")
    ws["A1"] = "Q2b – Missing và outlier của hồ sơ (trên toàn bộ tập EWS)"; ws["A1"].font = F(bold=True, size=14)
    ws["A2"] = "Số lượng, tỷ lệ thiếu và thống kê mô tả. Công thức Excel trên sheet Data_Profile; bỏ qua ô trống."; ws["A2"].font = F(italic=True, color="666666")
    ws["A3"] = "Tổng số dòng"; ws["A3"].font = F(bold=True); ws["B3"] = f"=COUNTA({R('app_id')})"; ws["B3"].number_format = "#,##0"
    hdr(ws, 4, ["Đặc trưng", "Missing", "% thiếu", "Min", "P1", "Trung vị", "P99", "Max", "> P99", "% > P99", "Trung bình", "Hướng xử lý"])
    for i, v in enumerate(cr.NUM_COLS):
        r = 5 + i; rg = R(v)
        put(ws, r, 1, v, bold=True)
        put(ws, r, 2, f'=COUNTIFS({rg},"")', "#,##0"); put(ws, r, 3, f"=B{r}/$B$3", "0.0%")
        put(ws, r, 4, f"=MIN({rg})", "#,##0.0"); put(ws, r, 5, f"=PERCENTILE({rg},0.01)", "#,##0.0")
        put(ws, r, 6, f"=MEDIAN({rg})", "#,##0.0"); put(ws, r, 7, f"=PERCENTILE({rg},0.99)", "#,##0.0")
        put(ws, r, 8, f"=MAX({rg})", "#,##0.0"); put(ws, r, 9, f'=COUNTIF({rg},">"&G{r})', "#,##0")
        put(ws, r, 10, f"=I{r}/COUNT({rg})", "0.0%"); put(ws, r, 11, f"=AVERAGE({rg})", "#,##0.0")
        put(ws, r, 12, TREAT[v], wrap=True); ws.row_dimensions[r].height = 42 if len(TREAT[v]) > 70 else 28
    r = 5 + len(cr.NUM_COLS) + 1
    ws.cell(row=r, column=1, value="Biến phân loại (đếm bằng Python): channel, customer_type, province, region, occupation, home_status – KHÔNG có giá trị thiếu.").font = F(italic=True)
    ws.cell(row=r + 2, column=1, value="Cách đọc").font = F(bold=True)
    for k, t in enumerate(["Missing = COUNTIFS(cột, \"\") = số ô trống.",
                           "Min … Max = MIN, PERCENTILE(0,01), MEDIAN, PERCENTILE(0,99), MAX.",
                           "> P99 = COUNTIF(cột, \">\"&P99): ứng viên ngoại lai cần xem lại (quy ước của công cụ).",
                           "Thiếu có thể mang ý nghĩa nghiệp vụ (không có thẻ, chưa có tài khoản tiền gửi): KHÔNG tự thay bằng 0."]):
        ws.cell(row=r + 3 + k, column=1, value=t).font = F()
    ws.column_dimensions["A"].width = 22
    for c in "BCDEFGHIJK": ws.column_dimensions[c].width = 11
    ws.column_dimensions["L"].width = 80; ws.freeze_panes = "B5"

    # ------------------------------------------------------------------ Q2c
    ws = wb.create_sheet("Q2c_Missing_bad_rate")
    ws["A1"] = "Q2c – Bad rate của nhóm thiếu so với danh mục (Good + Bad)"; ws["A1"].font = F(bold=True, size=14)
    ws["A2"] = "Bad = target gốc (90+ ngày trong 12 tháng đầu), CHỈ để phân tích xem 'thiếu' có mang thông tin rủi ro không."; ws["A2"].font = F(italic=True, color="666666")
    hdr(ws, 4, ["Đặc trưng", "Số hồ sơ thiếu", "Số Bad thiếu", "BR thiếu", "BR có dữ liệu", "BR danh mục", "Nhận xét"])
    tg, pc = R("target"), R("perf_class")
    put(ws, 10, 1, "Bad rate danh mục", bold=True); put(ws, 10, 6, f'=COUNTIFS({tg},1)/(COUNTIFS({tg},0)+COUNTIFS({tg},1))', "0.00%")
    for i, v in enumerate(["income_mil", "work_months", "card_util_pct", "deposit_avg_3m_mil"]):
        r = 5 + i; rg = R(v)
        put(ws, r, 1, v, bold=True)
        put(ws, r, 2, f'=COUNTIFS({rg},"",{tg},0)+COUNTIFS({rg},"",{tg},1)', "#,##0")
        put(ws, r, 3, f'=COUNTIFS({rg},"",{tg},1)', "#,##0"); put(ws, r, 4, f"=C{r}/B{r}", "0.0%")
        put(ws, r, 5, f'=COUNTIFS({rg},"<>",{tg},1)/(COUNTIFS({rg},"<>",{tg},0)+COUNTIFS({rg},"<>",{tg},1))', "0.0%")
        put(ws, r, 6, "=$F$10", "0.0%")
        put(ws, r, 7, f'=IF(D{r}>1.5*F{r},"Thiếu rủi ro hơn hẳn: giữ thành nhóm riêng",IF(D{r}<F{r}/1.5,"Thiếu an toàn hơn: giữ thành nhóm riêng","Gần mức trung bình: giữ nhóm riêng vì có ý nghĩa nghiệp vụ"))')
    ws["A12"] = "Quy ước: thiếu rủi ro/an toàn hơn rõ rệt khi lệch quá 1,5 lần bad rate danh mục. Gợi ý trả lời: income_mil và work_months – không khai là dấu hiệu rủi ro; card_util (không có thẻ) và deposit (không có TK tiền gửi) là nhóm lớn có ý nghĩa nghiệp vụ nên giữ thành nhóm riêng."
    ws["A12"].alignment = WRAP; ws.merge_cells("A12:G12"); ws.row_dimensions[12].height = 45
    ws.column_dimensions["A"].width = 22
    for c in "BCDEF": ws.column_dimensions[c].width = 15
    ws.column_dimensions["G"].width = 58

    # ------------------------------------------------------------------ Outlier rules
    ws = wb.create_sheet("Outlier_Rules")
    ws["A1"] = "Quy tắc giá trị bất thường & số vi phạm"; ws["A1"].font = F(bold=True, size=14)
    ws["A2"] = "Ô vàng là ngưỡng, đổi được; số vi phạm tự tính lại. Phải khớp THRESH trong clean_rules.py."; ws["A2"].font = F(italic=True, color="666666")
    hdr(ws, 4, ["Quy tắc", "Biến", "Điều kiện bất thường", "Ngưỡng", "Số vi phạm", "% vi phạm", "Cách xử lý", "Hàm / cờ trong clean_rules.py"])
    a, inc, dti, cu, wm, cic, d6, d12 = (R(x) for x in ["age", "income_mil", "dti_pct", "card_util_pct", "work_months", "cic_hist_months", "dpd_cnt_6m", "dpd_cnt_12m"])
    rules = [
        ("R01a", "age", "age < ngưỡng", 18, lambda t: f'=COUNTIFS({a},"<"&D{t})', "Lỗi nhập liệu → kẹp về nhóm biên gần nhất (18) + cờ", "clean_profile → f_age_invalid"),
        ("R01b", "age", "age > ngưỡng", 75, lambda t: f'=COUNTIFS({a},">"&D{t})', "Lỗi nhập liệu → kẹp về nhóm biên gần nhất (75) + cờ", "clean_profile → f_age_invalid"),
        ("R02", "income_mil", "income_mil > ngưỡng (triệu)", 500, lambda t: f'=COUNTIFS({inc},">"&D{t})', "Ngoại lai cực lớn / lỗi đơn vị → chặn trên (cap) ở 500 + cờ", "_fix_income → f_income_outlier"),
        ("R03", "dti_pct", "dti_pct > ngưỡng (%)", 200, lambda t: f'=COUNTIFS({dti},">"&D{t})', "Cực đoan nhưng có thể xảy ra → giữ nguyên giá trị + cờ (cap_dti=False)", "clean_profile → f_dti_outlier"),
        ("R04", "card_util_pct", "card_util_pct > ngưỡng (%)", 100, lambda t: f'=COUNTIFS({cu},">"&D{t})', "Vượt hạn mức, có thể có thật → giữ giá trị + cờ", "clean_profile → f_card_over100"),
        ("R05", "work_months", "work_months > (age−18)×12", "—", lambda t: f"=SUMPRODUCT(--({a}>=18),--({wm}>({a}-18)*12))", "Không vi phạm → không cần xử lý", "outlier_report"),
        ("R06", "cic_hist_months", "cic_hist_months > (age−18)×12", "—", lambda t: f"=SUMPRODUCT(--({a}>=18),--({cic}>({a}-18)*12))", "Không vi phạm → không cần xử lý", "outlier_report"),
        ("R07", "dpd_cnt_6m", "dpd_cnt_6m > dpd_cnt_12m", "—", lambda t: f"=SUMPRODUCT(--({d6}>{d12}))", "Không vi phạm → không cần xử lý", "outlier_report"),
        ("R08", "dpd_cnt_12m", "dpd_cnt_12m > cic_hist_months", "—", lambda t: f"=SUMPRODUCT(--({d12}>{cic}))", "Không vi phạm → không cần xử lý", "outlier_report"),
    ]
    for i, (rid, v, cond, th, fm, how, fn) in enumerate(rules):
        r = 5 + i
        put(ws, r, 1, rid, bold=True); put(ws, r, 2, v); put(ws, r, 3, cond)
        put(ws, r, 4, th, "0", fill=YEL if th != "—" else None); put(ws, r, 5, fm(r), "#,##0"); put(ws, r, 6, f"=E{r}/Q2b_Missing_outliers!$B$3", "0.00%")
        put(ws, r, 7, how, wrap=True); put(ws, r, 8, fn, wrap=True); ws.row_dimensions[r].height = 30
    ws["A15"] = ("Lưu ý: số trong data_dictionary.csv (122 tuổi, 76 thu nhập, 29 DTI, 2.139 card_util) được đếm trên các phạm vi khác nhau nên không khớp hoàn toàn. "
                 "Hãy dùng số đếm trực tiếp ở đây (trên tập EWS).")
    ws["A15"].alignment = WRAP; ws.merge_cells("A15:H15"); ws.row_dimensions[15].height = 30
    for c, w in zip("ABCDEFGH", [9, 17, 30, 10, 13, 11, 55, 34]): ws.column_dimensions[c].width = w

    # ------------------------------------------------------------------ Drift
    ws = wb.create_sheet("Drift_Income")
    ws["A1"] = "Drift thu nhập theo tháng nộp hồ sơ"; ws["A1"].font = F(bold=True, size=14)
    ws["A2"] = ("Từ 01/07/2023 biểu mẫu LOS yêu cầu khai cả thu nhập khác → thu nhập khai báo tăng ~25% (trung vị 12 → 15 triệu). "
                "Trung vị tính sau khi chặn trên (cap) thu nhập > 500 về 500; đây là giá trị Python (Excel thuần không có hàm trung vị theo nhóm).")
    ws["A2"].alignment = WRAP; ws.merge_cells("A2:F2"); ws.row_dimensions[2].height = 42
    hdr(ws, 4, ["Tháng (yyyymm)", "Số hồ sơ", "% thiếu income", "Trung vị income (triệu)", "Trước/Sau 07/2023"])
    dr = cr.drift_report(df)
    for i, row in dr.iterrows():
        r = 5 + i; ym = int(row.app_ym)
        put(ws, r, 1, ym, "0"); put(ws, r, 2, f"=COUNTIFS({R('app_ym')},A{r})", "#,##0")
        put(ws, r, 3, f'=COUNTIFS({R("app_ym")},A{r},{R("income_mil")},"")/B{r}', "0.0%")
        put(ws, r, 4, float(row.median_income), "0.0"); put(ws, r, 5, f'=IF(A{r}>=202307,"Sau","Trước")')
    end = 4 + len(dr)
    put(ws, end + 2, 1, "Trung vị trước", bold=True); put(ws, end + 2, 4, float(dr[dr.app_ym < 202307].median_income.median()), "0.0")
    put(ws, end + 3, 1, "Trung vị sau", bold=True); put(ws, end + 3, 4, float(dr[dr.app_ym >= 202307].median_income.median()), "0.0")
    put(ws, end + 4, 1, "Tỷ số sau/trước", bold=True); put(ws, end + 4, 4, f"=D{end+3}/D{end+2}", "0.00")
    ch = LineChart(); ch.title = "Trung vị thu nhập theo tháng nộp hồ sơ"; ch.height = 7.5; ch.width = 16
    ch.add_data(Reference(ws, min_col=4, min_row=4, max_row=end), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=5, max_row=end))
    ch.legend = None; ch.title.overlay = False; ch.roundedCorners = False; ch.x_axis.delete = False; ch.y_axis.delete = False
    ch.y_axis.scaling.min = 0; ws.add_chart(ch, "G4")
    for c, w in zip("ABCDE", [18, 12, 15, 22, 18]): ws.column_dimensions[c].width = w

    # ------------------------------------------------------------------ Quy tắc xử lý
    ws = wb.create_sheet("Quy_tac_xu_ly")
    ws["A1"] = "Danh sách quy tắc xử lý (chốt) & biến bị loại"; ws["A1"].font = F(bold=True, size=14)
    hdr(ws, 3, ["Nhóm", "Biến", "Vấn đề", "Quyết định", "Lý do / căn cứ", "Hàm trong clean_rules.py"])
    rows = [
        ("Missing", "income_mil, work_months", "Thiếu 4,5% / 10,7%", "Giữ trống + cờ f_*_missing", "Nhóm thiếu có bad rate cao gấp ~1,7× (Q2c): không khai là dấu hiệu rủi ro", "clean_profile"),
        ("Missing", "card_util_pct", "Thiếu 30%", "Giữ trống + cờ f_card_missing", "Thiếu nghĩa là không có thẻ (ý nghĩa nghiệp vụ)", "clean_profile"),
        ("Missing", "deposit_avg_3m_mil", "Thiếu 38%", "Giữ trống + cờ f_deposit_missing", "Thiếu nghĩa là chưa có tài khoản tiền gửi", "clean_profile"),
        ("Missing", "mọi biến số", "Cần điền khi huấn luyện", "Không thay bằng 0; điền trung vị fit trên Dev (tùy chọn) và vẫn giữ cờ", "Tránh rò rỉ từ OOT", "fit_medians, impute_median"),
        ("Outlier", "age", "<18 hoặc >75 (122 dòng)", "Kẹp về nhóm biên gần nhất [18, 75] + cờ f_age_invalid", "Lỗi nhập liệu, giữ lại quan sát và đưa về cận hợp lệ gần nhất", "clean_profile"),
        ("Outlier", "income_mil", ">500 (76 dòng)", "Chặn trên (cap) ở 500 + cờ f_income_outlier", "Giảm tác động của giá trị ngoại lai cực lớn, giữ lại tín hiệu thu nhập cao", "clean_profile"),
        ("Outlier", "dti_pct", ">200 (18 dòng)", "Giữ nguyên giá trị + cờ f_dti_outlier", "Cực đoan nhưng có thể xảy ra thực tế (mặc định cap_dti=False)", "clean_profile"),
        ("Outlier", "card_util_pct", ">100 (1.734 dòng)", "Giữ giá trị + cờ f_card_over100", "Chi tiêu vượt hạn mức có thể có thật", "clean_profile"),
        ("Drift", "income_mil", "Đứt gãy từ 07/2023 (+25%)", "Gắn income_period; KHÔNG hiệu chỉnh mặc định", "Hiệu chỉnh ×1,25 cho trước 07/2023 là tùy chọn, cần nhóm đồng ý (adjust_income_drift)", "clean_profile"),
        ("Leakage", ", ".join(C.LEAKAGE_COLS), "Kết quả/thông tin tương lai hoặc nhạy cảm", "LOẠI khỏi input mô hình", "Quy tắc chống data leakage của nhóm", "drop_leakage"),
        ("Leakage", "restr_mob", "Cơ cấu có thể xảy ra trong tương lai", "Chỉ dùng cờ restr_flag_t (≤ t) – do W4 tạo", "Quy tắc chống leakage", "(features.py)"),
        ("Phân tích", "perf_class, target", "Dùng tính Q2c", "Chỉ phân tích, không là input", "—", "drop_leakage"),
    ]
    for i, row in enumerate(rows):
        for j, v in enumerate(row): put(ws, 4 + i, 1 + j, v, wrap=True, bold=(j == 0))
        ws.row_dimensions[4 + i].height = 44
    for c, w in zip("ABCDEF", [11, 30, 30, 36, 52, 24]): ws.column_dimensions[c].width = w

    # ------------------------------------------------------------------ Data
    ws = wb.create_sheet("Data_Profile")
    for j, c in enumerate(DATA_COLS):
        x = ws.cell(row=1, column=1 + j, value=c); x.font = F(bold=True)
    sub = df.reindex(columns=DATA_COLS)
    for row in sub.itertuples(index=False):
        ws.append([None if pd.isna(v) else (v.item() if hasattr(v, "item") else v) for v in row])
    ws.freeze_panes = "B2"
    wb.move_sheet("Data_Profile", offset=0)
    wb.calculation.fullCalcOnLoad = True
    wb.save(path)


def main():
    df = cr.load_profile()
    C.INTERIM.mkdir(parents=True, exist_ok=True); C.OUT.mkdir(parents=True, exist_ok=True)
    cr.load_clean_profile().to_csv(C.INTERIM / "customer_profile_clean.csv", index=False)
    build(df, C.OUT / "W2_Customer_Profile_DQ.xlsx")
    print("Đã tạo outputs/W2_Customer_Profile_DQ.xlsx và data/interim/customer_profile_clean.csv")


if __name__ == "__main__":
    main()