"""Verify checksums and reconcile the published CSV, HTML, Excel and OOT data."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import load_workbook
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ews.artifacts import verify_artifacts

def verify(out):
    manifest = verify_artifacts(out)
    summary = json.loads((out / "run_summary.json").read_text(encoding="utf-8"))
    scores = pd.read_csv(out / "scored.csv", dtype={"app_id": str}, float_precision="round_trip")
    existing = scores.dpd_current.ge(30)
    assert len(scores) == summary["snapshot_total"]
    assert scores.app_id.is_unique
    assert scores.snap_date.str[:7].eq(summary["snapshot_month"]).all()
    assert scores.alert_level.value_counts().to_dict() == summary["snapshot_alerts"]
    assert scores.alert_level.eq("Existing 30+").equals(existing)
    assert scores.loc[existing, "pd_3m"].isna().all()
    assert scores.loc[~existing, "pd_3m"].between(0, 1).all()

    html = (out / "dashboard.html").read_text(encoding="utf-8")
    data, _ = json.JSONDecoder().raw_decode(html.split("const d = ", 1)[1])
    assert data["summary"] == summary
    fields = ["app_id", "cohort", "mob", "dpd_current", "pd_3m", "alert_level", "reason"]
    dashboard = pd.DataFrame(data["loans"], columns=fields)
    pd.testing.assert_frame_equal(dashboard, scores[fields], check_dtype=False, atol=1e-14)

    book = load_workbook(out / "EWS_Excel.xlsx", read_only=True, data_only=True)
    try:
        overview = book["00_Overview"]
        assert overview["B9"].value == summary["snapshot_month"]
        assert overview["B10"].value == len(scores)
        assert overview["B11"].value == summary["run_id"]
        for level, count, share in overview.iter_rows(min_row=2, max_row=6, max_col=3, values_only=True):
            assert count == summary["snapshot_alerts"].get(level, 0)
            assert np.isclose(share, count / len(scores))
        alert_rows = book["05_EWS_Alerts"].values
        columns = list(next(alert_rows))
        alerts = pd.DataFrame(alert_rows, columns=columns)
        expected = scores.groupby("alert_level", sort=False).head(80)
        alerts["snap_date"] = pd.to_datetime(alerts.snap_date).dt.strftime("%Y-%m-%d")
        pd.testing.assert_frame_equal(
            alerts, expected[columns].reset_index(drop=True), check_dtype=False, atol=1e-14
        )
        raw_rows = book["01_Raw_AsOf"].values
        raw_columns = list(next(raw_rows))
        raw = pd.DataFrame(raw_rows, columns=raw_columns)
        assert raw.app_id.equals(alerts.app_id)
        for mob in range(1, 25):
            assert raw.loc[alerts.mob.lt(mob), f"dpd_{mob:02d}"].isna().all()
    finally:
        book.close()

    if manifest["kind"] == "development":
        for cutoff, model in summary["models"].items():
            predictions = pd.read_csv(out / f"oot_predictions_{cutoff}.csv.gz", float_precision="round_trip")
            y = predictions[f"Target_{cutoff}_3M"]
            assert y.sum() == model["oot"]["events"]
            assert len(y) == model["oot"]["n"]
            for key, metric in [("average_precision", average_precision_score),
                                ("roc_auc", roc_auc_score), ("brier", brier_score_loss)]:
                assert np.isclose(metric(y, predictions.pd_3m), model["oot"][key])
    print(f"PASS · {manifest['kind']} · {summary['run_id'][:8]} · {len(scores):,} snapshots")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("outputs"))
    verify(parser.parse_args().out)
