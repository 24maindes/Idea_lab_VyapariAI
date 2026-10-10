"""
make_api_overview.py - writes docs/api_overview.md from the REAL routes of the app (so it can never be out of date).

    python scripts/make_api_overview.py            (from the backend folder)
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))        # so "app" can be imported when run as a script

os.environ.setdefault("DATABASE_URL", "sqlite://")
from app.main import app  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "docs" / "api_overview.md"
MODULES = [("Authentication", "/api/auth"), ("Shop", "/api/shop"), ("Products", "/api/products"), ("Suppliers", "/api/suppliers"),
           ("Purchases", "/api/purchases"), ("Sales", "/api/sales"), ("Inventory", "/api/inventory"), ("Activity", "/api/activity"),
           ("Reference market prices", "/api/reference"), ("Fair-price analysis", "/api/analysis"), ("Price forecasting", "/api/forecast"),
           ("Alerts and anomaly detection", "/api/alerts"), ("Recommendations", "/api/recommendations"), ("Dashboard", "/api/dashboard"),
           ("CSV import", "/api/import"), ("AI advisor", "/api/advisor"), ("System", "/api/health")]


def first_line(text: str | None) -> str:
    if not text:
        return ""
    line = text.strip().splitlines()[0].strip()
    return re.sub(r"\s+", " ", line).rstrip(".")


def main() -> None:
    spec = app.openapi()
    rows = []
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            rows.append((method.upper(), path, first_line(op.get("description") or op.get("summary")), bool(op.get("security"))))
    lines = ["# API overview", "", "Generated from the running app by `python scripts/make_api_overview.py`. "
             "All JSON keys are camelCase; money is rupees per unit; dates are `YYYY-MM-DD`. Every endpoint marked **Yes** needs the header "
             "`Authorization: Bearer <token>` (get the token from `/api/auth/login`) and only ever returns the logged-in user's own shop data. "
             "Interactive documentation: `/docs`.", ""]
    used = set()
    for title, prefix in MODULES:
        mine = [r for r in rows if r[1].startswith(prefix)]
        if not mine:
            continue
        used.update(mine)
        lines += [f"## {title}", "", "| Method | Path | Purpose | Auth required |", "|---|---|---|---|"]
        for m, p, d, a in sorted(mine, key=lambda r: (r[1], r[0])):
            lines.append(f"| {m} | `{p}` | {d.replace('|', '/')} | {'Yes' if a else 'No'} |")
        lines.append("")
    lines.append(f"Total: {len(rows)} operations.")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({len(rows)} operations, {sum(1 for r in rows if not r[3])} public)")


if __name__ == "__main__":
    main()
