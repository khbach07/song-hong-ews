"""Create a small, explicitly synthetic W3/W4 teaching example."""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ews.artifacts import publication
from ews.build_panel import make_targets, summarize_labels, wide_to_long
from ews.config import DPD_COLS, INTERIM
from ews.features import dpd_features

CASES = [
    ("CLEAN", [0, 0, 0, 0, 0, 0], None),
    ("EVENT30", [0, 4, 12, 18, 35, 0], None),
    ("EVENT90", [0, 0, 21, 38, 95, 0], None),
    ("ALREADY30", [0, 15, 32, 15, 12, 3], None),
    ("CLOSED", [0, 0, 0, 10], 4),
    ("MISSING", [0, 0, 0, 0, None, 0], None),
]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=INTERIM / "example")
    args = parser.parse_args()
    perf = pd.DataFrame([
        {"app_id": f"DEMO_{key}", "cohort": "Dev", "open_month": pd.Timestamp("2024-01-01"),
         "close_mob": close, "restr_mob": float("nan"), "mob_observed": len(dpd),
         **dict(zip(DPD_COLS, dpd + [None] * (len(DPD_COLS) - len(dpd))))}
        for key, dpd, close in CASES
    ])
    history = wide_to_long(perf)
    panel = make_targets(history)
    with publication(args.out) as staging:
        for name, frame in [
            ("synthetic_performance", perf), ("panel_target", panel),
            ("features", dpd_features(history)), ("label_summary", summarize_labels(panel)),
        ]:
            frame.to_csv(staging / f"{name}.csv", index=False, encoding="utf-8-sig")
    print(args.out.resolve())

if __name__ == "__main__":
    main()
