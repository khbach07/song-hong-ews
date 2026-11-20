"""W3 · Point-in-time loan-month snapshots, prospective labels & 07_Backtesting."""
from pathlib import Path
import numpy as np
import pandas as pd

from .config import (
    DEV,
    DPD_CMP,
    DPD_COLS,
    DPD_MAIN,
    HORIZON,
    MOB_MIN,
    OOT,
    OUT,
    PANEL_TARGET,
    PERF,
)


# 1. CHUYỂN BẢNG DPD TỪ DẠNG WIDE SANG DẠNG LONG THEO KHÓA (app_id, mob)
def wide_to_long(perf: pd.DataFrame) -> pd.DataFrame:
    """Trải các cột dpd_01..dpd_24 thành từng dòng (app_id, mob).
    Giữ lại các ô DPD bị thiếu trong chuỗi quan sát để phép shift(-1..-3)
    phản ánh đúng khoảng cách tháng lịch.
    """
    df = perf.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["open_month"]):
        df["open_month"] = pd.to_datetime(df["open_month"])
    if "cohort" not in df.columns:
        df["cohort"] = "UNKNOWN"

    parts = []
    opened = df["open_month"].dt.to_period("M")

    for mob, column in enumerate(DPD_COLS, start=1):
        # Chỉ giữ các tháng nằm trong kỳ quan sát và chưa tất toán ở tháng trước đó
        observed = df["mob_observed"].ge(mob)
        closed_before = df["close_mob"].lt(mob)
        keep = observed & ~closed_before

        block = df.loc[keep, ["app_id", "cohort", "close_mob", "restr_mob"]].copy()
        block["open_month"] = df.loc[keep, "open_month"]
        block["mob"] = mob
        block["snap_date"] = (opened[keep] + mob).dt.to_timestamp()
        block["dpd"] = df.loc[keep, column].astype("float32")
        parts.append(block)

    return pd.concat(parts, ignore_index=True).sort_values(
        ["app_id", "mob"], ignore_index=True
    )


# 2. GẮN NHÃN TARGET 30+ VÀ 90+ TRONG 3 THÁNG TIẾP THEO
def make_targets(long_df: pd.DataFrame) -> pd.DataFrame:
    """Tạo nhãn Target_30_3M (chính) và Target_90_3M (so sánh) cho từng snapshot."""
    group = long_df.groupby("app_id", sort=False)

    # Lấy DPD của 3 tháng tương lai: t+1, t+2, t+3
    future = pd.concat(
        [group["dpd"].shift(-offset) for offset in range(1, HORIZON + 1)],
        axis=1,
    )

    # Điều kiện snapshot hợp lệ tại tháng t:
    # - Từ MOB 3 trở đi, có DPD tại tháng t và khoản vay chưa tất toán tại/trước t
    eligible_snapshot = (
        long_df["mob"].ge(MOB_MIN)
        & long_df["dpd"].notna()
        & (long_df["close_mob"].isna() | long_df["close_mob"].gt(long_df["mob"]))
    )

    result = long_df.loc[
        eligible_snapshot, ["app_id", "mob", "snap_date", "cohort"]
    ].copy()

    # Đủ 3 tháng tương lai và không tất toán trước khi hết cửa sổ t+3
    complete = future.notna().all(axis=1) & (
        long_df["close_mob"].isna() | long_df["close_mob"].ge(long_df["mob"] + HORIZON)
    )
    result["full_followup"] = complete.loc[eligible_snapshot]

    for threshold in (DPD_MAIN, DPD_CMP):
        at_risk = long_df["dpd"].lt(threshold)          # Chưa chạm ngưỡng tại t (tránh risk-at-entry)
        hit = future.ge(threshold).any(axis=1)          # Có ít nhất 1 tháng trong t+1..t+3 đạt ngưỡng

        label = pd.Series(pd.NA, index=long_df.index, dtype="Int8")
        label.loc[at_risk & complete] = 0               # Đủ 3 tháng và không phát sinh sự kiện
        label.loc[at_risk & hit] = 1                    # Phát sinh sự kiện trong 3 tháng tới

        closed_early = long_df["close_mob"].notna() & long_df["close_mob"].le(
            long_df["mob"] + HORIZON
        )
        status = np.select(
            [~at_risk, hit, complete, closed_early],
            [
                "already_at_threshold",
                "event_observed",
                "complete_no_event",
                "closed_early",
            ],
            default="incomplete_followup",
        )

        result[f"Target_{threshold}_3M"] = label.loc[eligible_snapshot]
        result[f"status_{threshold}"] = status[eligible_snapshot.to_numpy()]

    result["label_end"] = (
        result["snap_date"].dt.to_period("M") + HORIZON
    ).dt.to_timestamp()
    return result.reset_index(drop=True)


# 3. TỔNG HỢP SỐ LIỆU CHO SHEET 07_BACKTESTING
def summarize_labels(panel: pd.DataFrame) -> pd.DataFrame:
    """Bảng 1 (07_Backtesting): Thống kê số lượng & tỷ trọng từng trạng thái gán nhãn."""
    rows = []
    for cutoff in (DPD_MAIN, DPD_CMP):
        status_col = f"status_{cutoff}"
        for cohort, part in panel.groupby("cohort", sort=False):
            counts = part[status_col].value_counts()
            total = len(part)
            for status_name, cnt in counts.items():
                rows.append(
                    {
                        "target_type": f"Target_{cutoff}_3M",
                        "cohort": cohort,
                        "status": status_name,
                        "snapshots": int(cnt),
                        "share_pct": round(cnt / total * 100, 2) if total else 0.0,
                    }
                )
    return pd.DataFrame(rows)


def build_backtesting_tables(panel: pd.DataFrame, out_dir: Path = OUT) -> dict:
    """Tạo các bảng đối chiếu thực tế (và đối chiếu dự báo nếu đã có output từ W5/W6)
    để đưa vào sheet 07_Backtesting.
    """
    valid = panel.loc[panel["full_followup"]].copy()
    valid["snap_month"] = valid["snap_date"].dt.strftime("%Y-%m")

    # Bảng 2: Tỷ lệ quá hạn thực tế theo tháng snapshot (so sánh 30+ vs 90+)
    by_month = (
        valid.groupby(["cohort", "snap_month"], as_index=False)
        .agg(
            snapshots=("app_id", "size"),
            events_30=("Target_30_3M", "sum"),
            actual_rate_30=("Target_30_3M", "mean"),
            events_90=("Target_90_3M", "sum"),
            actual_rate_90=("Target_90_3M", "mean"),
        )
        .sort_values(["cohort", "snap_month"], ignore_index=True)
    )

    # Nếu W5 đã chạy ra oot_predictions_30.csv.gz, ghép thêm PD dự báo trung bình để đối chiếu
    oot_pred_file = out_dir / "oot_predictions_30.csv.gz"
    if oot_pred_file.exists():
        oot_pred = pd.read_csv(oot_pred_file, parse_dates=["snap_date"])
        oot_pred["snap_month"] = oot_pred["snap_date"].dt.strftime("%Y-%m")
        pred_month = oot_pred.groupby("snap_month", as_index=False).agg(
            mean_predicted_pd=("pd_3m", "mean")
        )
        by_month = by_month.merge(pred_month, on="snap_month", how="left")

    # Bảng 3: Đối chiếu theo cấp cảnh báo Green/Yellow/Orange/Red (nếu đã có scored.csv)
    by_alert = pd.DataFrame()
    scored_file = out_dir / "scored.csv"
    if scored_file.exists():
        scored = pd.read_csv(scored_file, parse_dates=["snap_date"])
        merged = scored.merge(
            panel[["app_id", "mob", "Target_30_3M", "Target_90_3M"]],
            on=["app_id", "mob"],
            how="left",
        )
        total_events_30 = merged["Target_30_3M"].sum()
        by_alert = (
            merged.groupby("alert_level", as_index=False)
            .agg(
                snapshots=("app_id", "size"),
                mean_pd=("pd_3m", "mean"),
                actual_events_30=("Target_30_3M", "sum"),
                actual_rate_30=("Target_30_3M", "mean"),
                actual_events_90=("Target_90_3M", "sum"),
                actual_rate_90=("Target_90_3M", "mean"),
            )
        )
        if total_events_30 and total_events_30 > 0:
            by_alert["event_capture_30"] = by_alert["actual_events_30"] / total_events_30

    return {
        "label_summary": summarize_labels(panel),
        "backtest_by_month": by_month,
        "backtest_by_alert": by_alert,
    }


# 4. KIỂM THỬ NGHIỆM THU 5 TÌNH HUỐNG BIÊN & CHẠY ĐỘC LẬP W3
def verify_w3_cases() -> None:
    """Kiểm chứng 5 nhóm tình huống nghiệm thu trong W3_TARGET_LABELING.md."""
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

    out = make_targets(wide_to_long(sample)).set_index("app_id").loc[
        lambda d: d["mob"] == 3
    ]

    assert out.loc["FULL_CLEAN", "Target_30_3M"] == 0
    assert out.loc["HIT_30", "Target_30_3M"] == 1 and out.loc["HIT_30", "Target_90_3M"] == 0
    assert out.loc["HIT_90", "Target_90_3M"] == 1
    assert out.loc["MISSING_M6_AFTER_30", "Target_30_3M"] == 1
    assert pd.isna(out.loc["MISSING_M6_AFTER_30", "Target_90_3M"])
    assert pd.isna(out.loc["CLOSED_EARLY", "Target_30_3M"])
    assert out.loc["CLOSED_EARLY", "status_30"] == "closed_early"
    assert pd.isna(out.loc["ALREADY_30", "Target_30_3M"])
    assert out.loc["ALREADY_30", "Target_90_3M"] == 0


def load_eligible_perf(
    perf_path: Path = PERF, dev_path: Path = DEV, oot_path: Path = OOT
) -> pd.DataFrame:
    """Đọc dữ liệu gốc và lọc đúng phạm vi khoản vay hợp lệ của nhóm (loại Excluded)."""
    perf = pd.read_csv(perf_path)
    dev = pd.read_csv(dev_path, usecols=["app_id", "perf_class"]).assign(cohort="DEV")
    oot = pd.read_csv(oot_path, usecols=["app_id", "perf_class"]).assign(cohort="OOT")
    profiles = pd.concat([dev, oot], ignore_index=True)

    merged = perf.merge(profiles, on="app_id", how="inner")
    eligible = merged.loc[merged["perf_class"].ne("Excluded")].drop(
        columns=["perf_class"]
    )
    eligible["open_month"] = pd.to_datetime(eligible["open_month"])
    return eligible.reset_index(drop=True)


def main() -> None:
    verify_w3_cases()
    print("[W3] Đã kiểm chứng xong 6 tình huống biên nghiệm thu.")

    OUT.mkdir(parents=True, exist_ok=True)
    perf = load_eligible_perf()
    long_df = wide_to_long(perf)
    panel = make_targets(long_df)

    # Xuất file trao đổi panel_target.csv và panel_target.csv.gz
    panel.to_csv(PANEL_TARGET, index=False, encoding="utf-8-sig")
    panel.to_csv(
        OUT / "panel_target.csv.gz",
        index=False,
        compression={"method": "gzip", "compresslevel": 1},
    )

    # Xuất các bảng phục vụ sheet 07_Backtesting
    tables = build_backtesting_tables(panel, OUT)
    tables["label_summary"].to_csv(
        OUT / "w3_label_summary.csv", index=False, encoding="utf-8-sig"
    )
    tables["backtest_by_month"].to_csv(
        OUT / "w3_backtesting_07.csv", index=False, encoding="utf-8-sig"
    )

    try:
        with pd.ExcelWriter(OUT / "W3_07_Backtesting.xlsx") as writer:
            tables["label_summary"].to_excel(
                writer, sheet_name="07_Label_Summary", index=False
            )
            tables["backtest_by_month"].to_excel(
                writer, sheet_name="07_Backtesting", index=False
            )
            if not tables["backtest_by_alert"].empty:
                tables["backtest_by_alert"].to_excel(
                    writer, sheet_name="07_Alert_Backtest", index=False
                )
    except Exception:
        pass

    print(f"[W3] Hoàn tất! Số dòng panel_target: {len(panel):,}")
    print(f"[W3] Đã xuất: {PANEL_TARGET.name}, w3_label_summary.csv, w3_backtesting_07.csv")


if __name__ == "__main__":
    main()