"""Generate an offline, filterable EWS monitoring dashboard."""
import json

from .thresholds import ACTIONS, LEVELS

def write_dashboard(out, live, summary, backtest, thresholds):
    fields = ["app_id", "cohort", "mob", "dpd_current", "pd_3m", "alert_level", "reason"]
    payload = {
        "loans": json.loads(live[fields].to_json(orient="values")),
        "summary": summary,
        "monthly": json.loads(backtest.to_json(orient="records")),
        "thresholds": thresholds.lower_pd.tolist(),
        "actions": ACTIONS,
        "levels": LEVELS + ["Existing 30+"],
    }
    data = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    template = out_template()
    (out / "dashboard.html").write_text(template.replace("__EWS_DATA__", data), encoding="utf-8")

def out_template():
    from pathlib import Path
    return Path(__file__).with_name("dashboard.html").read_text(encoding="utf-8")
