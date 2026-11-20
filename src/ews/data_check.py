"""W1 · Source validation, joins and scope."""
from pathlib import Path

import numpy as np
import pandas as pd

from . import clean_rules as cr
from .config import DPD_COLS

FILES = {
    "perf": "song_hong_perf_monthly.csv",
    "dev": "song_hong_dev_2023.csv",
    "oot": "song_hong_oot_2024H1.csv",
}
PROFILE = ["app_date", "decision", "perf_class", *cr.NUM_COLS, *cr.CAT_COLS]
PERFORMANCE = ["open_month", "mob_observed", "close_mob", "restr_mob", *DPD_COLS]

def read_source(path: Path, required: list[str]) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype={"app_id": "string"}, encoding="utf-8-sig")
    missing = set(["app_id", *required]).difference(frame.columns)
    if missing:
        raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
    frame["app_id"] = frame.app_id.str.strip()
    if frame.app_id.isna().any() or frame.app_id.eq("").any() or not frame.app_id.is_unique:
        raise ValueError(f"{path.name}: app_id is blank or duplicated")
    return frame

def load_data(raw: Path):
    perf = read_source(raw / FILES["perf"], PERFORMANCE)
    dev = read_source(raw / FILES["dev"], [*PROFILE, "exclusion_reason"])
    oot = read_source(raw / FILES["oot"], PROFILE)
    if dev.app_id.isin(oot.app_id).any():
        raise ValueError("Dev and OOT contain overlapping app_id.")
    perf["open_month"] = pd.to_datetime(perf.open_month, format="%Y-%m", errors="raise")
    if perf.open_month.isna().any():
        raise ValueError("Missing open_month")
    for column in PERFORMANCE[1:]:
        perf[column] = pd.to_numeric(perf[column], errors="raise")
        values = perf[column].dropna().to_numpy()
        if not np.isfinite(values).all() or (values % 1 != 0).any():
            raise ValueError(f"{column}: expected finite integer values")
    if not perf.mob_observed.between(1, len(DPD_COLS)).all():
        raise ValueError("mob_observed is outside 1–24 or missing")
    for column in ["close_mob", "restr_mob"]:
        perf[column] = perf[column].replace(0, np.nan)
        if not perf[column].dropna().between(1, len(DPD_COLS)).all():
            raise ValueError(f"{column}: MOB outside 1–24")
    if perf[DPD_COLS].lt(0).any().any():
        raise ValueError("Negative DPD")

    profile = pd.concat([dev.assign(cohort="Dev"), oot.assign(cohort="OOT")],
                        ignore_index=True)
    profile["app_date"] = pd.to_datetime(profile.app_date, errors="raise")
    if profile.app_date.isna().any():
        raise ValueError("Missing app_date")
    joined = perf.merge(profile[["app_id", "cohort", "app_date", "decision",
                                 "perf_class", "exclusion_reason"]],
                        on="app_id", how="left", validate="one_to_one")
    scope_excluded = joined.exclusion_reason.isin(
        ["Nhân viên ngân hàng", "Gian lận đã xác nhận"]
    ) | (joined.cohort.eq("OOT") & joined.perf_class.eq("Excluded"))
    eligible = joined.decision.eq("Approved") & ~scope_excluded
    audit = pd.DataFrame(
        [{"source": FILES[key], "rows": len(frame), "columns": len(frame.columns),
          "unique_app_ids": frame.app_id.nunique(),
          "match_perf": int(frame.app_id.isin(perf.app_id).sum())}
         for key, frame in [("perf", perf), ("dev", dev), ("oot", oot)]]
    )
    coverage = {
        "perf_unmatched_profile": int(joined.cohort.isna().sum()),
        "scope_excluded": int(scope_excluded.sum()),
        "eligible_loans": int(eligible.sum()),
        "profile_matches": {
            name: {"matched": int(frame.app_id.isin(perf.app_id).sum()),
                   "approved": int(frame.decision.eq("Approved").sum()),
                   "approved_matched": int((frame.decision.eq("Approved") &
                                            frame.app_id.isin(perf.app_id)).sum())}
            for name, frame in [("Dev", dev), ("OOT", oot)]
        },
        "approval_month_differs_from_open_proxy": int(
            (joined.app_date.notna() & joined.app_date.dt.to_period("M").ne(
                joined.open_month.dt.to_period("M"))).sum()
        ),
    }
    scoped = joined.loc[eligible, perf.columns.tolist() + ["cohort"]].copy()
    selected = profile[profile.app_id.isin(scoped.app_id)].copy()
    selected["app_ym"] = selected.app_date.dt.year * 100 + selected.app_date.dt.month
    return scoped, selected, audit, coverage
