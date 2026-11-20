"""W3 · Point-in-time loan-month snapshots and prospective outcome labels."""
import numpy as np
import pandas as pd

from .config import DPD_CMP, DPD_COLS, DPD_MAIN, HORIZON, MOB_MIN

def wide_to_long(perf: pd.DataFrame) -> pd.DataFrame:
    """Chuyển dữ liệu DPD từ dạng wide (dpd_01..dpd_24) sang dạng long theo (app_id, mob)."""
    parts = []
    opened = perf.open_month.dt.to_period("M")
    for mob, column in enumerate(DPD_COLS, start=1):
        observed = perf.mob_observed.ge(mob)
        closed_before = perf.close_mob.lt(mob)
        keep = observed & ~closed_before
        block = perf.loc[keep, ["app_id", "cohort", "close_mob", "restr_mob"]].copy()
        block["open_month"] = perf.loc[keep, "open_month"]
        block["mob"] = mob
        block["snap_date"] = (opened[keep] + mob).dt.to_timestamp()
        block["dpd"] = perf.loc[keep, column].astype("float32")
        parts.append(block)
    return pd.concat(parts, ignore_index=True).sort_values(
        ["app_id", "mob"], ignore_index=True
    )

def make_targets(long_df: pd.DataFrame) -> pd.DataFrame:
    """Gắn nhãn Target_30_3M và Target_90_3M trong cửa sổ 3 tháng tiếp theo."""
    group = long_df.groupby("app_id", sort=False)
    future = pd.concat(
        [group.dpd.shift(-offset) for offset in range(1, HORIZON + 1)],
        axis=1,
    )
    eligible_snapshot = (
        long_df.mob.ge(MOB_MIN)
        & long_df.dpd.notna()
        & (long_df.close_mob.isna() | long_df.close_mob.gt(long_df.mob))
    )
    result = long_df.loc[
        eligible_snapshot, ["app_id", "mob", "snap_date", "cohort"]
    ].copy()
    complete = future.notna().all(axis=1) & (
        long_df.close_mob.isna() | long_df.close_mob.ge(long_df.mob + HORIZON)
    )
    result["full_followup"] = complete.loc[eligible_snapshot]
    for threshold in (DPD_MAIN, DPD_CMP):
        at_risk = long_df.dpd.lt(threshold)
        hit = future.ge(threshold).any(axis=1)
        label = pd.Series(pd.NA, index=long_df.index, dtype="Int8")
        label.loc[at_risk & complete] = 0
        label.loc[at_risk & hit] = 1
        closed_early = long_df.close_mob.notna() & long_df.close_mob.le(
            long_df.mob + HORIZON
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
        result.snap_date.dt.to_period("M") + HORIZON
    ).dt.to_timestamp()
    return result.reset_index(drop=True)

def summarize_labels(panel: pd.DataFrame) -> pd.DataFrame:
    """Tổng hợp số lượng và tỷ trọng từng trạng thái gán nhãn (phục vụ 07_Backtesting)."""
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