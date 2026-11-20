"""Unit & acceptance tests for W3 target labeling (build_panel.py)."""
import numpy as np
import pandas as pd

from src.ews.build_panel import make_targets, summarize_labels, wide_to_long


def _loan(app_id, dpd_map, mob_obs=6, close_mob=np.nan):
    row = {
        "app_id": app_id,
        "cohort": "OOT",
        "open_month": pd.Timestamp("2024-01-01"),
        "mob_observed": mob_obs,
        "close_mob": close_mob,
        "restr_mob": np.nan,
    }
    for m in range(1, 25):
        row[f"dpd_{m:02d}"] = dpd_map.get(m, np.nan)
    return row


def test_w3_target_cases():
    sample = pd.DataFrame(
        [
            # 1. Đủ kỳ không sự kiện
            _loan("FULL_CLEAN", {1: 0, 2: 0, 3: 0, 4: 0, 5: 15, 6: 29}, mob_obs=6),
            # 2. Chạm đúng 30 ở t+2, dưới 90 cả 3 tháng
            _loan("HIT_30", {1: 0, 2: 0, 3: 8, 4: 10, 5: 30, 6: 0}, mob_obs=6),
            # 3. Chạm đúng 90 ở t+3
            _loan("HIT_90", {1: 0, 2: 0, 3: 0, 4: 0, 5: 45, 6: 90}, mob_obs=6),
            # 4. Thiếu tháng 6 nhưng tháng 5 đã chạm 31 -> 30+ vẫn bằng 1, 90+ là NA
            _loan("MISSING_M6_AFTER_30", {1: 0, 2: 0, 3: 8, 4: 10, 5: 31}, mob_obs=5),
            # 5. Tất toán sớm ở MOB 5 -> NA (closed_early)
            _loan("CLOSED_EARLY", {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}, mob_obs=8, close_mob=5),
            # 6. Đã ở ngưỡng 30 tại MOB 3 -> Target_30_3M = NA, Target_90_3M = 0
            _loan("ALREADY_30", {1: 0, 2: 15, 3: 30, 4: 45, 5: 60, 6: 0}, mob_obs=6),
        ]
    )

    panel = make_targets(wide_to_long(sample))
    out = panel.set_index("app_id").loc[lambda d: d["mob"] == 3]

    assert out.loc["FULL_CLEAN", "Target_30_3M"] == 0
    assert out.loc["HIT_30", "Target_30_3M"] == 1 and out.loc["HIT_30", "Target_90_3M"] == 0
    assert out.loc["HIT_90", "Target_90_3M"] == 1
    assert out.loc["MISSING_M6_AFTER_30", "Target_30_3M"] == 1
    assert pd.isna(out.loc["MISSING_M6_AFTER_30", "Target_90_3M"])
    assert pd.isna(out.loc["CLOSED_EARLY", "Target_30_3M"])
    assert out.loc["CLOSED_EARLY", "status_30"] == "closed_early"
    assert pd.isna(out.loc["ALREADY_30", "Target_30_3M"])
    assert out.loc["ALREADY_30", "Target_90_3M"] == 0

    summary = summarize_labels(panel)
    assert not summary.empty


if __name__ == "__main__":
    test_w3_target_cases()
    print("All W3 tests passed!")