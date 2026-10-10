# PostgreSQL audit

**Result:** 442 of the 450 backend tests pass on a real PostgreSQL 16 server (embedded `pgserver`); all 450 pass on SQLite. The 8 tests in
`b_test_retrain.py` (model training) were not completed on PostgreSQL (the run did not finish in the time available), so they are verified on SQLite only. Run it yourself: `TEST_DATABASE_URL=postgresql+psycopg2://user:pass@localhost/test_db pytest` (use an EMPTY test database; its tables are
dropped and recreated for every test).

| Risk | Where | What was done |
|---|---|---|
| `postgres://` URL scheme from hosting services | `database.py` | converted to `postgresql://` automatically |
| Connections closed by the server | `database.py` | `pool_pre_ping=True` for non-SQLite |
| NULL ordering differs (SQLite: first, PostgreSQL: last) | dashboard "low stock" ratio | wrapped in `coalesce(..., -1)` so both databases order the same |
| `ORDER BY` a text label | cheapest supplier query | now orders by the aggregate expression |
| Case sensitive text comparison | e-mail, product and supplier names | compared with `lower()` on both sides; e-mails are stored in lower case |
| Boolean comparison | alerts `is_read`, `is_best` | always `.is_(True/False)` |
| `ILIKE` search | products | works on both (SQLAlchemy renders `lower() LIKE` on SQLite) |
| Window functions (`row_number`) | inventory, sales summary, dashboard | supported by SQLite 3.25+ and PostgreSQL |
| Duplicate reference rows | `reference_prices` | unique constraint (commodity, market, date) for new databases; loader is idempotent |
| Bulk insert size | `load_reference` | inserted in chunks of 5000 rows |
| Dates as text | all date columns | real `DATE` columns, compared with Python `date` objects |
| Existing SQLite files | any change to a model | `create_all` never alters existing tables: delete the old `.db` file (or write a migration) after model changes |
