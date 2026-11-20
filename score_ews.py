"""Publish one historical snapshot with the frozen model."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import pandas as pd

from ews.artifacts import month_key, publication, seal
from ews.config import OUT, RAW
from ews.pipeline import publish_snapshot
from ews.scoring import HistoricalScorer

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", required=True, help="Historical month in YYYY-MM")
    parser.add_argument("--raw", type=Path, default=RAW)
    parser.add_argument("--model-dir", type=Path, default=OUT)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        month = month_key(args.month)
        with publication(args.out) as staging:
            scorer = HistoricalScorer(args.raw, args.model_dir)
            scorer.prepare()
            live = scorer.score(month)
            summary = dict(
                scorer.summary, snapshot_month=month, snapshot_total=len(live),
                snapshot_alerts=live.alert_level.value_counts().to_dict(),
            )
            backtest = pd.read_csv(args.model_dir / "backtest_monthly.csv")
            publish_snapshot(staging, args.model_dir, scorer.performance, scorer.profiles,
                             scorer.inventory, live, summary, backtest, scorer.thresholds)
            seal(staging, "snapshot")
    except (ValueError, OSError) as error:
        parser.exit(2, f"EWS: {error}\n")
    print(f"{month} · {len(live):,} snapshots · {args.out.resolve()}")

if __name__ == "__main__":
    main()
