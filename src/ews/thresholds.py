"""W6 · Derive probability cutoffs using validation only."""
import numpy as np
import pandas as pd

LEVELS = ["Green", "Yellow", "Orange", "Red"]
ACTIONS = {
    "Green": "Theo dõi định kỳ",
    "Yellow": "Rà soát lịch trả và nhắc trước hạn",
    "Orange": "Liên hệ khoản vay, kiểm tra nguyên nhân và ghi nhận cam kết",
    "Red": "Ưu tiên rà soát ngay và chuyển chuyên viên quản lý rủi ro",
    "Existing 30+": "Chuyển luồng quản lý khoản vay đã quá hạn",
}

def choose_thresholds(scores: np.ndarray, capacities: tuple[float, ...]) -> pd.DataFrame:
    cutoffs = [0.0]
    ordered = np.sort(np.asarray(scores))
    for capacity in capacities:
        count = int(np.floor(len(ordered) * capacity))
        boundary = ordered[len(ordered) - count - 1]
        first_higher = np.searchsorted(ordered, boundary, side="right")
        cutoff = (boundary + ordered[first_higher]) / 2 if first_higher < len(ordered) else 1.01
        cutoffs.append(float(cutoff))
    return pd.DataFrame({"level": LEVELS, "lower_pd": cutoffs,
                         "target_cumulative_share": [1.0, *capacities]})

def assign_level(scores, thresholds: pd.DataFrame):
    indices = np.searchsorted(thresholds.lower_pd.to_numpy(), scores, side="right") - 1
    return np.asarray(LEVELS)[indices]

def reason_codes(features: pd.DataFrame) -> pd.Series:
    def explain(row):
        reasons = []
        if row.dpd_current >= 30:
            return "DPD hiện tại từ 30 ngày"
        if row.dpd_current > 0:
            reasons.append(f"DPD hiện tại {row.dpd_current:.0f} ngày")
        if row.dpd_delta_1 > 0:
            reasons.append(f"DPD tăng {row.dpd_delta_1:.0f} ngày so với tháng trước")
        if row.late_months_3 >= 2:
            reasons.append(f"Quá hạn {row.late_months_3:.0f}/3 tháng gần nhất")
        if row.restructured:
            reasons.append("Đã cơ cấu")
        return " · ".join(reasons) if reasons else "Theo dõi theo điểm mô hình"
    return features.apply(explain, axis=1)
