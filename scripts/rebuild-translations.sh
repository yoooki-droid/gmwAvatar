#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

cd "$BACKEND_DIR"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt >/dev/null

python - <<'PY'
from sqlalchemy import desc

from app.api.reports import _refresh_report_translations
from app.database import SessionLocal
from app.models import MeetingReport

db = SessionLocal()
ok = 0
skipped = 0
failed = 0

try:
    reports = db.query(MeetingReport).order_by(desc(MeetingReport.id)).all()
    for report in reports:
        script = (report.script_final or '').strip()
        if not script:
            skipped += 1
            continue
        try:
            highlights = [h.highlight_text for h in sorted([x for x in report.highlights if x.kind == 'final'], key=lambda x: x.seq)][:2]
            _refresh_report_translations(db, report, highlights)
            ok += 1
            print(f"[OK] report_id={report.id} title={report.title}")
        except Exception as exc:
            failed += 1
            print(f"[FAILED] report_id={report.id} err={exc}")
    db.commit()
    print(f"done: ok={ok}, skipped={skipped}, failed={failed}")
except Exception:
    db.rollback()
    raise
finally:
    db.close()
PY
