import numpy as np
import pandas as pd

from ews.build_panel import make_targets, wide_to_long
from ews.config import DPD_COLS
from ews.features import dpd_features
from ews.thresholds import assign_level, choose_thresholds

def sample(dpd, close=None, restr=5):
    return {"app_id": "TEST", "cohort": "Dev", "open_month": pd.Timestamp("2023-11"),
            "mob_observed": len(dpd), "close_mob": close if close else np.nan,
            "restr_mob": restr, **dict(zip(DPD_COLS, dpd + [np.nan] * (24 - len(dpd))))}

def test_point_in_time_and_calendar():
    baseline = sample([0, 0, 12, 18, 32, 5])
    changed = dict(baseline, dpd_05=95)
    a, b = [wide_to_long(pd.DataFrame([s])) for s in [baseline, changed]]
    fa, fb = [dpd_features(p).query("mob == 3") for p in [a, b]]
    pd.testing.assert_frame_equal(fa, fb)
    assert fa.iloc[0].snap_date == pd.Timestamp("2024-02-01")
    assert fa.iloc[0].restructured == 0
    pa, pb = [make_targets(p).iloc[0] for p in [a, b]]
    assert (pa.Target_30_3M, pa.Target_90_3M) == (1, 0)
    assert (pb.Target_30_3M, pb.Target_90_3M) == (1, 1)
    assert pa.full_followup

def test_early_observed_event_and_closure():
    loan = sample([0, 0, 12, 45, None, None], close=4)
    long = wide_to_long(pd.DataFrame([loan]))
    row = make_targets(long).iloc[0]
    assert row.Target_30_3M == 1
    assert not row.full_followup
    assert pd.isna(row.Target_90_3M)
    assert row.status_90 == "closed_early"
    assert list(dpd_features(long).mob) == [3]

def test_independent_risk_sets_and_missing_window():
    loan = sample([10, 20, 31, 70, None, 20])
    panel = make_targets(wide_to_long(pd.DataFrame([loan])))
    assert panel.iloc[0].status_30 == "already_at_threshold"
    assert panel.iloc[0].status_90 == "incomplete_followup"
    assert pd.isna(panel.iloc[0].Target_90_3M)

def test_threshold_ties_do_not_exceed_validation_capacity():
    scores = np.array([0.1] * 80 + [0.6] * 10 + [0.8] * 10)
    table = choose_thresholds(scores, (0.20, 0.10, 0.03))
    levels = assign_level(scores, table)
    assert (levels != "Green").mean() <= 0.20
    assert (levels == "Red").mean() <= 0.03
