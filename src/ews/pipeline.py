"""Run the full development, backtesting and reporting pipeline."""
import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from . import clean_rules as cr
from .build_panel import make_targets, wide_to_long
from .config import DPD_COLS, OUT, RAW
from .data_check import FILES, load_data
from .features import BEHAVIOR, PROFILE, dpd_features
from .report import write_dashboard
from .thresholds import ACTIONS, LEVELS, assign_level, choose_thresholds, reason_codes
from .train_model import fit_models, metrics, split_dev_oot

KEY = ["app_id", "mob", "snap_date"]
CAPACITY = (0.20, 0.10, 0.03)
SCORE_FIELDS = KEY + ["cohort", "dpd_current", "dpd_mean_3", "dpd_max_3",
                      "late_months_3", "dpd_delta_1", "pd_3m",
                      "alert_level", "reason", "action"]

def score_snapshot(live, model, fields, thresholds):
    live = live.copy()
    live["pd_3m"] = np.nan
    ready = live.dpd_current.lt(30)
    live["alert_level"] = "Existing 30+"
    if ready.any():
        scores = model.predict_proba(live.loc[ready, fields])[:, 1]
        live.loc[ready, "pd_3m"] = scores
        live.loc[ready, "alert_level"] = assign_level(scores, thresholds)
    live["reason"] = reason_codes(live)
    live["action"] = live.alert_level.map(ACTIONS)
    priority = {level: rank for rank, level in enumerate([*LEVELS, "Existing 30+"])}
    return live.sort_values(
        ["alert_level", "pd_3m", "app_id"],
        key=lambda column: column.map(priority) if column.name == "alert_level" else column,
        ascending=[False, False, True],
    )

def mask_future_dpd(sample_raw, live):
    mob = live.mob.to_numpy()
    raw = sample_raw[["app_id", "open_month", *DPD_COLS]].copy()
    raw[DPD_COLS] = raw[DPD_COLS].where(np.arange(1, 25) <= mob[:, None])
    return raw

def write_excel_inputs(out, performance, profiles, live, inventory):
    sample = live.groupby("alert_level", sort=False).head(80)
    raw = performance.set_index("app_id").loc[sample.app_id].reset_index()
    raw = mask_future_dpd(raw, sample)
    ids = pd.Index(sample.app_id)
    profile = profiles.set_index("app_id").loc[ids].reset_index()
    tables = {
        "raw": raw, "profiles": profile[["app_id", *PROFILE]],
        "features": sample[KEY + [col for col in BEHAVIOR if col not in KEY]],
        "alerts": sample[SCORE_FIELDS], "inventory": inventory,
    }
    payload = {key: json.loads(frame.to_json(orient="split", date_format="iso"))
               for key, frame in tables.items()}
    (out / "excel_snapshot.json").write_text(json.dumps(payload, ensure_ascii=False),
                                            encoding="utf-8")

def save_csv(out, filename, frame):
    frame.to_csv(out / filename, index=False, encoding="utf-8-sig")

def alert_metrics(scored, target):
    cells = []
    events = scored[target].sum()
    for level in LEVELS:
        part = scored.loc[scored.alert_level.eq(level)]
        hits = int(part[target].sum())
        cells.append({"level": level, "snapshots": len(part), "events": hits,
                      "alert_share": len(part) / len(scored),
                      "event_rate": hits / len(part) if len(part) else None,
                      "event_capture": hits / events})
    return cells

def run(raw: Path, out: Path, month: str | None):
    out.mkdir(parents=True, exist_ok=True)
    performance, profiles, inventory, coverage = load_data(raw)
    print(f"Sources checked · {len(performance):,} eligible loans", flush=True)
    clean = cr.clean_profile(profiles)
    save_csv(out, "source_inventory.csv", inventory)
    for name, frame in [
        ("missing_profile.csv", cr.missing_report(profiles)),
        ("outliers_profile.csv", cr.outlier_report(profiles)),
        ("income_drift.csv", cr.drift_report(profiles)),
    ]:
        save_csv(out, name, frame)

    long = wide_to_long(performance)
    panel = make_targets(long)
    features = dpd_features(long).merge(clean[["app_id", *PROFILE]],
                                        on="app_id", validate="many_to_one")
    table = panel.merge(features, on=KEY, validate="one_to_one").merge(
        performance[["app_id", "open_month"]], on="app_id", validate="many_to_one"
    )
    if len(table) != len(panel) or len(table) != len(features):
        raise ValueError("Snapshot coverage mismatch between targets and features")
    del long, features
    panel.to_csv(out / "panel_target.csv.gz", index=False, compression={"method": "gzip", "compresslevel": 1})
    table[KEY + [column for column in table if column not in KEY and column not in panel
                 and column != "open_month"]].to_csv(
        out / "features.csv.gz", index=False, compression={"method": "gzip", "compresslevel": 1}
    )

    results = {}
    for cutoff in (30, 90):
        target = f"Target_{cutoff}_3M"
        splits = split_dev_oot(table, target)
        print(f"Training {target} · " + " · ".join(
            f"{key} {len(part):,}" for key, part in splits.items()), flush=True)
        champion, model, fields, val_scores, comparison, coef = fit_models(splits, target)
        save_csv(out, f"comparison_{cutoff}.csv", comparison)
        joblib.dump({"name": champion, "features": fields, "model": model, "target": target},
                    out / f"model_{cutoff}.joblib", compress=3)
        oot = splits["OOT"]
        scores = model.predict_proba(oot[fields])[:, 1]
        scored_oot = oot[KEY + ["dpd_current", target]].assign(pd_3m=scores)
        result = {
            "champion": champion, "features": fields,
            "splits": {name: {"snapshots": len(part), "loans": part.app_id.nunique(),
                              "events": int(part[target].sum()),
                              "first": str(part.snap_date.min().date()),
                              "last": str(part.snap_date.max().date()),
                              "label_end_max": str(part.label_end.max().date())}
                       for name, part in splits.items()},
            "oot": metrics(oot[target], scores),
            "oot_baseline": metrics(oot[target], oot.dpd_current, False),
        }
        if cutoff == 90:
            early = oot.dpd_current.lt(30).to_numpy()
            result["oot_current_dpd_below_30"] = metrics(oot.loc[early, target], scores[early])
        results[str(cutoff)] = result
        if cutoff == 30:
            thresholds = choose_thresholds(val_scores, CAPACITY)
            thresholds["validation_cumulative_share"] = [
                float((val_scores >= threshold).mean()) for threshold in thresholds.lower_pd
            ]
            save_csv(out, "thresholds.csv", thresholds)
            save_csv(out, "coef.csv", coef)
            scored_oot["alert_level"] = assign_level(scores, thresholds)
            result["alert_performance"] = alert_metrics(scored_oot, target)
            groups = scored_oot.assign(month=scored_oot.snap_date.dt.strftime("%Y-%m"))
            backtest = groups.groupby("month", as_index=False).agg(
                snapshots=(target, "size"), events=(target, "sum"),
                event_rate=(target, "mean"), mean_pd=("pd_3m", "mean")
            )
            calibration = scored_oot.assign(
                pd_band=pd.qcut(scored_oot.pd_3m, 10, duplicates="drop")
            ).groupby("pd_band", observed=True, as_index=False).agg(
                snapshots=(target, "size"), observed_rate=(target, "mean"),
                mean_pd=("pd_3m", "mean")
            )
            save_csv(out, "backtest_monthly.csv", backtest)
            save_csv(out, "calibration_30.csv", calibration)
            chosen_month = (pd.Period(month, freq="M") if month else
                            table.loc[table.cohort.eq("OOT"), "snap_date"].max().to_period("M"))
            if chosen_month.to_timestamp() < oot.snap_date.min():
                raise ValueError("Scoring month precedes the first post-validation OOT month")
            live = table.loc[table.snap_date.eq(chosen_month.to_timestamp())].copy()
            if live.empty:
                raise ValueError(f"No eligible snapshots for {chosen_month}")
            live = score_snapshot(live, model, fields, thresholds)
            save_csv(out, "scored.csv", live[SCORE_FIELDS])
            write_excel_inputs(out, performance, clean, live, inventory)
        scored_oot.to_csv(out / f"oot_predictions_{cutoff}.csv.gz", index=False, compression={"method": "gzip", "compresslevel": 1})

    counts = {key: int(value) for key, value in live.alert_level.value_counts().items()}
    summary = {
        "scope": coverage, "models": results, "snapshot_month": str(chosen_month),
        "snapshot_total": len(live), "snapshot_alerts": counts,
        "labels": {str(cutoff): {
            cohort: {key: int(value) for key, value in counts_in_cohort.items()}
            for cohort, counts_in_cohort in [
                (cohort, part[f"status_{cutoff}"].value_counts())
                for cohort, part in panel.groupby("cohort")
            ]} for cutoff in (30, 90)},
        "input_sha256": {key: hashlib.sha256((raw / file).read_bytes()).hexdigest()
                          for key, file in FILES.items()},
    }
    (out / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                         encoding="utf-8")
    write_dashboard(out, live, summary, backtest, thresholds)
    print(f"Finished · {out.resolve()}", flush=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=RAW)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--month", help="Historical scoring snapshot, YYYY-MM")
    args = parser.parse_args()
    with threadpool_limits(limits=2):
        run(args.raw, args.out, args.month)

if __name__ == "__main__":
    main()
