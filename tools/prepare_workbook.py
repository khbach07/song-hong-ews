"""Combine pipeline outputs into the input for tools/build_workbook.mjs."""
import argparse
import json
from pathlib import Path

import pandas as pd

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--model-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads((args.snapshot_dir / "excel_snapshot.json").read_text(encoding="utf-8"))
    payload["summary"] = json.loads((args.snapshot_dir / "run_summary.json").read_text(encoding="utf-8"))
    for name in ["thresholds", "backtest_monthly", "comparison_30", "comparison_90",
                 "calibration_30", "outliers_profile", "missing_profile"]:
        frame = pd.read_csv(args.model_dir / f"{name}.csv", float_precision="round_trip")
        payload[name] = json.loads(frame.to_json(orient="split", double_precision=15))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()
