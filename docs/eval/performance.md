# Performance (1 page)

**Machine / server:** [TODO: CPU, RAM, hosting]  **Database:** [TODO: SQLite / PostgreSQL]

Measured on 2026-10-09 against `http://127.0.0.1:8000` by `scripts/e2e_flow.py` (one request per step, includes the first call after a restart).

| Step | Response time (ms) | Result |
|---|---|---|
| signup a new user | 276 | PASS |
| create shop | 10 | PASS |
| create 3 products linked to market data | 27 | PASS |
| create 2 suppliers | 18 | PASS |
| record 6 purchases (one 42 % above market) | 125 | PASS |
| abnormal purchase flagged at once | 0 | PASS |
| record 10 sales | 71 | PASS |
| fair price - all products | 9 | PASS |
| fair price - one product (detail) | 6 | PASS |
| fair price - live check | 5 | PASS |
| forecast (7 days) | 30 | PASS |
| forecast model comparison | 4 | PASS |
| recommendations - what to buy | 139 | PASS |
| recommendations - selling price | 8 | PASS |
| suppliers - comparison | 6 | PASS |
| alerts - scan and list | 25 | PASS |
| inventory | 7 | PASS |
| dashboard summary | 35 | PASS |
| dashboard price trend | 9 | PASS |
| advisor chat | 28 | PASS |
| advisor chat (Hindi) | 9 | PASS |
| another user cannot see this shop's data | 279 | PASS |

**Total:** 1.1 s for 22 steps. First recommendations call includes loading the saved models.

**Targets:** simple reads under 200 ms, dashboard under 1 s, advisor answer under 8 s with Gemini (the offline answer is instant).
**Caching:** forecasts 10 min, recommendations and dashboard heavy part 60 s, advisor context 60 s; every write of a shop clears that shop's cache.
