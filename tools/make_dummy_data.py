"""Sinh dữ liệu GIẢ cùng cấu trúc để làm song song (không phải dữ liệu thật).
Chạy từ thư mục gốc repo:  python tools/make_dummy_data.py
Tạo: outputs/dummy_panel_target.csv, dummy_features.csv, dummy_scored.csv
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ews import config as C

rng = np.random.default_rng(0)
n_loans = 500
rows = [(f"SH23{i:06d}", m) for i in range(1, n_loans + 1) for m in range(C.MOB_MIN, C.MOB_MAX + 1)]
df = pd.DataFrame(rows, columns=C.KEY)
df["snap_date"] = pd.Timestamp("2023-06-01")
df["Target_30_3M"] = (rng.random(len(df)) < 0.05).astype(int)
df["Target_90_3M"] = (df["Target_30_3M"] & (rng.random(len(df)) < 0.5)).astype(int)
df["label_status"] = "Labeled"
C.OUT.mkdir(exist_ok=True)
df[C.PANEL_COLS].to_csv(C.OUT / "dummy_panel_target.csv", index=False)

feat = df[C.KEY].copy()
feat["dpd_t"] = np.where(df["Target_30_3M"] == 1, rng.integers(1, 40, len(df)), 0)
feat["dpd_avg_3m"] = feat["dpd_t"] * rng.random(len(df))
feat["dpd_max_3m"] = feat["dpd_t"]
feat["n_months_dpd_6m"] = rng.integers(0, 4, len(df))
feat.to_csv(C.OUT / "dummy_features.csv", index=False)

scored = df[C.KEY].copy()
scored["PD"] = np.clip(0.02 + 0.5 * df["Target_30_3M"] * rng.random(len(df)), 0, 1)
scored.to_csv(C.OUT / "dummy_scored.csv", index=False)
print("Đã tạo dữ liệu giả trong outputs/")
