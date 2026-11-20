"""Serve Sông Hồng EWS on loopback using frozen local artifacts."""
import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from ews.config import OUT, RAW
from ews.pipeline import SCORE_FIELDS
from ews.scoring import HistoricalScorer
from ews.thresholds import LEVELS

ASSETS = {"/": ("index.html", "text/html"), "/app.css": ("app.css", "text/css"),
          "/app.js": ("app.js", "text/javascript")}

def records(frame):
    return json.loads(frame.to_json(orient="records", date_format="iso", double_precision=15))

def handler_for(scorer):
    def table(name):
        return records(pd.read_csv(scorer.model_dir / f"{name}.csv"))
    metadata = {
        "months": scorer.months, "models": scorer.summary["models"],
        "thresholds": records(scorer.thresholds), "monthly": table("backtest_monthly"),
        "calibration": table("calibration_30"), "comparison": table("comparison_30"),
        "inventory": table("source_inventory"), "missing": table("missing_profile"),
        "drift": table("income_drift"),
    }

    class Handler(BaseHTTPRequestHandler):
        def send_bytes(self, body, content_type, status=200, filename=None):
            self.send_response(status)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; style-src 'self' 'unsafe-inline'")
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, value, status=200):
            self.send_bytes(json.dumps(value, ensure_ascii=False, allow_nan=False).encode(),
                            "application/json", status)

        def do_GET(self):
            url = urlsplit(self.path)
            if url.path in ASSETS:
                filename, content_type = ASSETS[url.path]
                self.send_bytes((ROOT / "web" / filename).read_bytes(), content_type)
                return
            if url.path == "/api/meta":
                self.send_json(metadata)
                return
            if url.path not in {"/api/snapshot", "/api/export"}:
                self.send_json({"error": "Đường dẫn không tồn tại"}, 404)
                return
            query = parse_qs(url.query)
            month = query.get("month", [""])[0]
            level = query.get("level", [""])[0]
            cohort = query.get("cohort", [""])[0]
            search = query.get("q", [""])[0].strip()
            try:
                page = int(query.get("page", ["1"])[0])
                if page < 1 or level not in ["", *LEVELS, "Existing 30+"] or cohort not in {"", "Dev", "OOT"}:
                    raise ValueError("Bộ lọc không hợp lệ")
                live = scorer.score(month)
            except ValueError as error:
                self.send_json({"error": str(error)}, 400)
                return
            matches = live
            if level:
                matches = matches.loc[matches.alert_level.eq(level)]
            if cohort:
                matches = matches.loc[matches.cohort.eq(cohort)]
            if search:
                matches = matches.loc[matches.app_id.str.contains(search, case=False, regex=False)]
            if url.path == "/api/export":
                exported = matches[SCORE_FIELDS].copy()
                # Keep externally supplied text inert when the CSV is opened in a spreadsheet.
                risky = exported.app_id.str.match(r"^[\s]*[=+@-]", na=False)
                exported.loc[risky, "app_id"] = "'" + exported.loc[risky, "app_id"]
                self.send_bytes(exported.to_csv(index=False).encode("utf-8-sig"),
                                "text/csv", filename=f"EWS-{month}.csv")
                return
            size = 20
            last = max(1, (len(matches) + size - 1) // size)
            page = min(page, last)
            self.send_json({
                "month": month, "total": len(live), "matched": len(matches),
                "counts": live.alert_level.value_counts().to_dict(),
                "eligible": int(live.pd_3m.notna().sum()),
                "page": page, "pages": last,
                "rows": records(matches.iloc[(page - 1)*size:page*size][SCORE_FIELDS]),
            })
    return Handler

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--raw", type=Path, default=RAW)
    parser.add_argument("--model-dir", type=Path, default=OUT)
    args = parser.parse_args()
    scorer = HistoricalScorer(args.raw, args.model_dir)
    print("Đang chuẩn bị lịch sử khoản vay…", flush=True)
    scorer.prepare()
    with HTTPServer(("127.0.0.1", args.port), handler_for(scorer)) as server:
        print(f"EWS · http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()
