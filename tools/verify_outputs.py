"""Reconcile the delivered CSV, dashboard, workbook and reported OOT metrics."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import load_workbook
from sklearn.metrics import average_precision_score, roc_auc_score

def verify(out):
    summary = json.loads((out / "run_summary.json").read_text(encoding="utf-8"))
    scores = pd.read_csv(out / "scored.csv")
    assert len(scores) == summary["snapshot_total"]
    assert scores.app_id.is_unique
    assert scores.alert_level.value_counts().to_dict() == summary["snapshot_alerts"]
    assert scores.loc[scores.dpd_current.ge(30), "pd_3m"].isna().all()
    assert scores.loc[scores.dpd_current.lt(30), "pd_3m"].between(0, 1).all()
    html = (out / "dashboard.html").read_text(encoding="utf-8")
    data = json.loads(html.split("const d=", 1)[1].split(";\nconst $=", 1)[0])
    assert len(data["loans"]) == len(scores)
    for cutoff, model in summary["models"].items():
        predictions = pd.read_csv(out / f"oot_predictions_{cutoff}.csv.gz")
        y = predictions[f"Target_{cutoff}_3M"]
        assert y.sum() == model["oot"]["events"]
        assert len(y) == model["oot"]["n"]
        assert np.isclose(average_precision_score(y, predictions.pd_3m),
                          model["oot"]["average_precision"])
        assert np.isclose(roc_auc_score(y, predictions.pd_3m), model["oot"]["roc_auc"])

    workbook_path = out / "EWS_Excel.xlsx"
    if workbook_path.exists():
        book = load_workbook(workbook_path, read_only=True, data_only=True)
        try:
            dash = book["06_Dashboard"]
            assert dash["B11"].value == len(scores)
            assert abs(dash["C11"].value - 1) < 1e-9
            alerts = book["05_EWS_Alerts"]
            source = scores.set_index("app_id")
            for row in alerts.iter_rows(min_row=6, values_only=True):
                if row[0]:
                    assert row[5] == source.loc[row[0], "alert_level"], row
            backtest = book["07_Backtesting"]
            monthly = pd.read_csv(out / "backtest_monthly.csv").set_index("month")
            for month, n, events, rate, _ in backtest.iter_rows(
                    min_row=6, max_row=5 + len(monthly), max_col=5, values_only=True):
                expected = monthly.loc[month]
                assert n == expected.snapshots and events == expected.events
                assert abs(rate - expected.event_rate) < 1e-10
        finally:
            book.close()
    print("PASS · snapshot, dashboard, OOT metrics and workbook (when present)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("outputs"))
    verify(parser.parse_args().out)
