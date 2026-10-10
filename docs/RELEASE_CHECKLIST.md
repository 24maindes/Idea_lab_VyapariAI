# Release checklist - VyapariAI v1.0

## 1. Fresh-clone test (do this on a different computer or a new folder)
1. `git clone <repo> vyapari-test && cd vyapari-test`
2. Follow the README from "Setup". Time yourself: it should take under 20 minutes.
3. `cd backend && python -m pytest -q` - all tests pass.
4. Start backend and frontend. Log in as `demo@vyapariai.com` / `demo1234`. Click every sidebar item once: no blank pages, no red errors.
5. With the server running: `python scripts/e2e_flow.py` - every step PASS.
6. Stop the backend, reload a page: you see a clear "cannot reach the server" message, not a blank page.
7. Search the repository for secrets: `git grep -n -i "api_key\|secret" -- . ":!*.md"` - no real keys. `.env` must NOT be committed.

## 2. Create the release zip (without node_modules, venv, .env, *.db)
Windows PowerShell, from the folder that contains `VyapariAI`:
```powershell
git -C VyapariAI archive --format=zip --prefix=VyapariAI/ -o VyapariAI_v1.0_source.zip HEAD
```
(`git archive` only contains committed files, so `node_modules`, `venv`, `.env`, `*.db` and `data/raw` are left out automatically.)
Without git: zip the folder but exclude `node_modules`, `venv`, `__pycache__`, `.env`, `*.db`, `backend/data/raw`, `frontend/dist`.
Check the zip: it must contain `backend/models_store/*.joblib`, `backend/data/reference_prices.csv`, `docs/`, and must NOT contain `.env`.

## 3. Tag the release
```bash
git add -A && git commit -m "Release v1.0"
git tag -a v1.0 -m "VyapariAI v1.0 - IDEA Lab submission"
git push origin main --tags
```

## 4. Submission folder
| File | Notes |
|---|---|
| `VyapariAI_v1.0_source.zip` | code, docs, trained models |
| `Report.pdf` | from `docs/report/report.md` (paste into Word / Google Docs, add screenshots, export PDF) |
| `Demo.mp4` | 7 minutes, follow `docs/report/demo_script.md` |
| `Screenshots/` | the 12 images from `docs/SCREENSHOTS.md` |
| `Synopsis.pdf` | the approved synopsis |
| `Slides.pptx` | 10 slides from `docs/report/slides_outline.md` |
| `README` and `docs/user_manual.md` | included in the zip |

## 5. Last-day checks
- [ ] Demo database re-seeded the same morning (`seed_demo`) so dates are current.
- [ ] Models retrained or still present (`models_store` has 15 files); `GEMINI_API_KEY` works (run `scripts/advisor_smoke.py`).
- [ ] `docs/eval/*.md` regenerated (`train_forecast`, `evaluate_anomaly`, `e2e_flow`, `make_eval_docs`, `advisor_eval`).
- [ ] Every `[TODO]` in the README and the report is filled in.
- [ ] Laptop charged, internet/hotspot ready, backup copy of the project on a pen drive, demo video available as a fallback.
