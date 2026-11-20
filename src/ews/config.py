"""Quy ước chung của nhóm (Bước 0). Không tự ý đổi – báo cả nhóm trước."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
OUT = ROOT / "outputs"

# File nguồn
PERF = RAW / "song_hong_perf_monthly.csv"       # nguồn chính (DPD theo MOB)
DEV = RAW / "song_hong_dev_2023.csv"            # hồ sơ 2023
OOT = RAW / "song_hong_oot_2024H1.csv"          # kiểm định out-of-time
# KHÔNG dùng: bureau_rejects, applications_2026Q2, perf_monthly.xlsx

# File trao đổi
PANEL_TARGET = OUT / "panel_target.csv"   # W3
FEATURES = OUT / "features.csv"           # W4
COEF = OUT / "coef.csv"                   # W5
THRESHOLDS = OUT / "thresholds.csv"       # W6

# Khóa & tham số
KEY = ["app_id", "mob"]
DPD_COLS = [f"dpd_{i:02d}" for i in range(1, 25)]
HORIZON = 3                  # tháng tương lai
DPD_MAIN, DPD_CMP = 30, 90   # Target_30_3M (chính), Target_90_3M (so sánh)
MOB_MIN, MOB_MAX = 3, 21     # phạm vi snapshot ban đầu

# Biến KHÔNG được đưa vào input mô hình (data leakage / nhạy cảm)
LEAKAGE_COLS = [
    "perf_class", "target", "max_dpd_12m", "exclusion_reason",
    "indeterminate_reason", "decision", "curr_max_cic_group", "gender",
]
# restr_mob chỉ dùng dạng cờ restr_flag_t = (restr_mob <= t)

# Cột file trao đổi (ĐỀ XUẤT – chốt theo sheet Interface_Files)
PANEL_COLS = ["app_id", "mob", "snap_date", "Target_30_3M", "Target_90_3M", "label_status"]

def snap_date(open_month: str, mob: int):
    """snap_date = open_month + mob tháng, trả về ngày đầu tháng (pandas.Timestamp).
    open_month dạng 'yyyy-mm'. Cả nhóm dùng đúng hàm này."""
    import pandas as pd
    return pd.Period(open_month, freq="M").to_timestamp() + pd.DateOffset(months=int(mob))
