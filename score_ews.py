"""Re-score a historical snapshot with the frozen model; no retraining."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import joblib
import pandas as pd
from threadpoolctl import threadpool_limits

from ews import clean_rules as cr
from ews.build_panel import wide_to_long
from ews.config import OUT, RAW
from ews.data_check import load_data
from ews.features import PROFILE, dpd_features
from ews.pipeline import SCORE_FIELDS, save_csv, score_snapshot, write_excel_inputs
from ews.report import write_dashboard

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", required=True, help="Historical month in YYYY-MM")
    parser.add_argument("--raw", type=Path, default=RAW)
    parser.add_argument("--model-dir", type=Path, default=OUT)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    month = pd.Period(args.month, freq="M")
    if args.out.resolve() == args.model_dir.resolve():
        parser.error("--out must differ from --model-dir")
    summary = json.loads((args.model_dir / "run_summary.json").read_text(encoding="utf-8"))
    oot_first = pd.Timestamp(summary["models"]["30"]["splits"]["OOT"]["first"])
    if month.to_timestamp() < oot_first:
        parser.error(f"Select {oot_first:%Y-%m} or later to score after validation label maturity")
    artifact = joblib.load(args.model_dir / "model_30.joblib")
    performance, profiles, inventory, _ = load_data(args.raw)
    clean = cr.clean_profile(profiles)
    live = dpd_features(wide_to_long(performance))
    live = live.loc[live.snap_date.eq(month.to_timestamp())].merge(
        clean[["app_id", "cohort", *PROFILE]], on="app_id", validate="one_to_one"
    )
    if live.empty:
        parser.error(f"No active snapshot for {month}")
    thresholds = pd.read_csv(args.model_dir / "thresholds.csv", float_precision="round_trip")
    with threadpool_limits(limits=2):
        live = score_snapshot(live, artifact["model"], artifact["features"], thresholds)
    args.out.mkdir(parents=True, exist_ok=True)
    save_csv(args.out, "scored.csv", live[SCORE_FIELDS])
    write_excel_inputs(args.out, performance, clean, live, inventory)
    backtest = pd.read_csv(args.model_dir / "backtest_monthly.csv")
    summary.update(snapshot_month=str(month), snapshot_total=len(live),
                   snapshot_alerts=live.alert_level.value_counts().astype(int).to_dict())
    write_dashboard(args.out, live, summary, backtest, thresholds)
    (args.out / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"{month} · {len(live):,} snapshots · {args.out.resolve()}")

if __name__ == "__main__":
    main()
