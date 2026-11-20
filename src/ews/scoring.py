"""Shared historical scoring service for CLI and local web."""
import json
from functools import lru_cache

import joblib
import pandas as pd
from threadpoolctl import threadpool_limits

from .clean_rules import clean_profile
from .build_panel import wide_to_long
from .data_check import load_data
from .features import PROFILE, dpd_features
from .pipeline import score_snapshot

class HistoricalScorer:
    def __init__(self, raw, model_dir):
        self.summary = json.loads((model_dir / "run_summary.json").read_text(encoding="utf-8"))
        self.thresholds = pd.read_csv(model_dir / "thresholds.csv", float_precision="round_trip")
        self.model_dir = model_dir
        self.raw = raw
        self.first_month = self.summary["models"]["30"]["splits"]["OOT"]["first"][:7]
        self._score_cached = lru_cache(maxsize=3)(self._score)

    def prepare(self):
        self.performance, profiles, self.inventory, _ = load_data(self.raw)
        self.profiles = clean_profile(profiles)
        features = dpd_features(wide_to_long(self.performance))
        features = features.loc[features.snap_date.ge(pd.Timestamp(self.first_month))]
        self.history = features.groupby("snap_date", sort=True)
        self.months = tuple(date.strftime("%Y-%m") for date in self.history.groups)
        self.artifact = joblib.load(self.model_dir / "model_30.joblib")

    def _score(self, month):
        live = self.history.get_group(pd.Timestamp(month)).merge(
            self.profiles[["app_id", "cohort", *PROFILE]], on="app_id", validate="one_to_one"
        )
        with threadpool_limits(limits=2):
            return score_snapshot(live, self.artifact["model"], self.artifact["features"], self.thresholds)

    def score(self, month):
        if month not in self.months:
            raise ValueError(f"Không có snapshot hợp lệ cho {month}")
        return self._score_cached(month)
