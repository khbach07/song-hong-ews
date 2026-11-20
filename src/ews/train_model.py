"""W5 · Temporal splits, model comparison and probability scoring."""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from .features import BEHAVIOR, PROFILE

VALIDATION_COHORT = pd.Timestamp("2023-09-01")
SEED = 42

def split_dev_oot(table, target):
    dev = table.cohort.eq("Dev")
    early = dev & table.open_month.lt(VALIDATION_COHORT)
    late = dev & ~early
    oot = table.cohort.eq("OOT")
    validation_start = table.loc[late, "snap_date"].min()
    oot_start = table.loc[oot, "snap_date"].min()
    known = table[target].notna() & table.full_followup
    result = {
        "Train": table.loc[early & known & table.label_end.lt(validation_start)],
        "Validation": table.loc[late & known & table.label_end.lt(oot_start)],
        "OOT": table.loc[oot & known],
    }
    for name, part in result.items():
        if part[target].nunique() != 2:
            raise ValueError(f"{target} / {name}: both classes required")
    return result

def candidates():
    return [
        ("Logistic Regression", BEHAVIOR, make_pipeline(
            SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(max_iter=500)
        )),
        ("Logistic Regression + hồ sơ", BEHAVIOR + PROFILE, make_pipeline(
            SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(max_iter=500)
        )),
        ("Decision Tree", BEHAVIOR + PROFILE, make_pipeline(
            SimpleImputer(strategy="median"),
            DecisionTreeClassifier(max_depth=4, min_samples_leaf=150, random_state=SEED)
        )),
        ("Random Forest", BEHAVIOR + PROFILE, make_pipeline(
            SimpleImputer(strategy="median"), RandomForestClassifier(
                n_estimators=100, max_depth=8, min_samples_leaf=80,
                max_samples=0.65, n_jobs=2, random_state=SEED
            )
        )),
        ("Gradient Boosting", BEHAVIOR + PROFILE, HistGradientBoostingClassifier(
            max_iter=100, max_leaf_nodes=12, min_samples_leaf=100,
            learning_rate=0.06, l2_regularization=3, random_state=SEED,
            early_stopping=False
        )),
    ]

def metrics(y, scores, probability=True):
    both_classes = y.nunique() == 2
    return {
        "n": len(y), "events": int(y.sum()), "event_rate": float(y.mean()),
        "average_precision": float(average_precision_score(y, scores)) if both_classes else None,
        "roc_auc": float(roc_auc_score(y, scores)) if both_classes else None,
        "brier": float(brier_score_loss(y, scores)) if probability else None,
        "mean_pd": float(np.mean(scores)) if probability else None,
    }

def fit_models(splits, target):
    train, val = splits["Train"], splits["Validation"]
    y_train, y_val = train[target].astype(int), val[target].astype(int)
    rows = [{"model": "DPD hiện tại", **metrics(y_val, val.dpd_current, False)}]
    fitted = {}
    for name, features, model in candidates():
        model.fit(train[features], y_train)
        scores = model.predict_proba(val[features])[:, 1]
        rows.append({"model": name, **metrics(y_val, scores)})
        fitted[name] = (model, features, scores)
    best = sorted(rows[1:], key=lambda r: (-r["average_precision"], r["brier"]))[0]
    model, features, val_scores = fitted[best["model"]]
    logistic, logistic_fields, _ = fitted["Logistic Regression + hồ sơ"]
    scaler, lr = logistic.steps[1][1], logistic.steps[2][1]
    slope = lr.coef_[0] / scaler.scale_
    coefficients = pd.DataFrame({
        "feature": logistic_fields, "coefficient": slope,
        "median": logistic.steps[0][1].statistics_,
    })
    coefficients.loc[len(coefficients)] = [
        "intercept", lr.intercept_[0] - np.dot(scaler.mean_, slope), np.nan
    ]
    return best["model"], model, features, val_scores, pd.DataFrame(rows), coefficients
