"""W4 · Features based exclusively on information available by the snapshot."""
import pandas as pd
from .config import MOB_MIN

BEHAVIOR = [
    "mob", "dpd_current", "dpd_mean_3", "dpd_max_3", "late_months_3",
    "dpd_delta_1", "dpd_max_6", "late_months_6", "dpd_obs_6", "restructured",
]
PROFILE = [
    "loan_amount_mil", "dti_pct", "cic_hist_months", "num_lenders",
    "inq_6m", "dpd_cnt_12m", "card_util_pct", "deposit_avg_3m_mil",
    "f_card_missing", "f_deposit_missing",
]

def dpd_features(long_df: pd.DataFrame) -> pd.DataFrame:
    group = long_df.groupby("app_id", sort=False)
    history = pd.concat([long_df.dpd, *[group.dpd.shift(lag) for lag in range(1, 6)]],
                        axis=1, ignore_index=True)
    last3 = history.iloc[:, :3]
    result = long_df[["app_id", "mob", "snap_date"]].copy()
    result["dpd_current"] = long_df.dpd
    result["dpd_mean_3"] = last3.mean(axis=1)
    result["dpd_max_3"] = last3.max(axis=1)
    result["late_months_3"] = last3.gt(0).sum(axis=1)
    result["dpd_delta_1"] = history[0] - history[1]
    result["dpd_max_6"] = history.max(axis=1)
    result["late_months_6"] = history.gt(0).sum(axis=1)
    result["dpd_obs_6"] = history.notna().sum(axis=1)
    result["restructured"] = long_df.restr_mob.le(long_df.mob).astype("int8")
    eligible = (result.mob.ge(MOB_MIN) & result.dpd_current.notna()
                & (long_df.close_mob.isna() | long_df.close_mob.gt(result.mob)))
    return result.loc[eligible].reset_index(drop=True)
