# VyapariAI Backend — Auth Module (Member 1: User & Shop Management)

This covers Login + Signup only, backed by a `users` table, matching the Seminar 1 scope
in the work plan (Auth & basic DB, no ML/RAG yet).

## Setup (VS Code)

```bash
cd vyapariai-backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

This auto-creates `vyapariai.db` (SQLite) with the `users` table on first run.
Open http://127.0.0.1:8000/docs to test the endpoints interactively.

Before running for real, change `SECRET_KEY` in `.env` to a random string.

## Endpoints

| Method | Route              | Body                                   | Returns                     |
|--------|--------------------|-----------------------------------------|------------------------------|
| POST   | /api/auth/signup   | `{ fullName, email, password }`         | `{ access_token, user }`     |
| POST   | /api/auth/login    | `{ email, password }`                   | `{ access_token, user }`     |
| GET    | /api/auth/me       | header: `Authorization: Bearer <token>` | `{ id, fullName, email }`    |

## Connecting to your React frontend (vyapariai)

CORS is already enabled for `http://localhost:5173` (Vite's default port).

In `Login.jsx`, replace the `handleSubmit` body:

```jsx
const handleSubmit = async (e) => {
  e.preventDefault();
  if (!email.trim() || !password.trim()) {
    setError("Please enter both email and password.");
    return;
  }
  try {
    const res = await fetch("http://127.0.0.1:8000/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Login failed");

    localStorage.setItem("vyapariToken", data.access_token);
    localStorage.setItem("vyapariUser", JSON.stringify(data.user));
    setError("");
    onLogin();
  } catch (err) {
    setError(err.message);
  }
};
```

In `Signup.jsx`, the same pattern applies inside `handleSubmit`, after validation passes:

```jsx
try {
  const res = await fetch("http://127.0.0.1:8000/api/auth/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      fullName: form.fullName,
      email: form.email,
      password: form.password,
    }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Signup failed");

  localStorage.setItem("vyapariToken", data.access_token);
  localStorage.setItem("vyapariUser", JSON.stringify(data.user));
  onSignup();
} catch (err) {
  setErrors({ email: err.message });
}
```

## Next tables (not included here)

Once this is working end-to-end, add `Shops` (for `ShopSetup.jsx`) and `Products` next —
same pattern: SQLAlchemy model in `models.py`, schema in `schemas.py`, router file,
included in `main.py`.
