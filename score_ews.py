"""Re-score a historical snapshot with the frozen model; no retraining."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import pandas as pd

from ews.config import OUT, RAW
from ews.pipeline import SCORE_FIELDS, save_csv, write_excel_inputs
from ews.report import write_dashboard
from ews.scoring import HistoricalScorer

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
    scorer = HistoricalScorer(args.raw, args.model_dir)
    if str(month) < scorer.first_month:
        parser.error(f"Select {scorer.first_month} or later to score after validation label maturity")
    scorer.prepare()
    try:
        live = scorer.score(str(month))
    except ValueError as error:
        parser.error(str(error))
    summary = scorer.summary
    thresholds = scorer.thresholds
    args.out.mkdir(parents=True, exist_ok=True)
    save_csv(args.out, "scored.csv", live[SCORE_FIELDS])
    write_excel_inputs(args.out, scorer.performance, scorer.profiles, live, scorer.inventory)
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
