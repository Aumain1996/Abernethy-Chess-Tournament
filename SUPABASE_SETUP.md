# Supabase Setup Guide — Match Data Persistence

This app uses [Supabase](https://supabase.com) (free) to store match scores persistently,
shared across all users visiting the Streamlit app.

> ⚠️ **Never paste your real Supabase credentials into this file.**
> Add them only to Streamlit Cloud Secrets or your local `.streamlit/secrets.toml`.

---

## Step 1 — Create a Free Supabase Project

1. Go to [https://supabase.com](https://supabase.com) and sign in with GitHub or email
2. Click **New Project**, give it a name (e.g. `chess-tournament`), set a database password, pick a region close to Perth
3. Wait ~1 minute for the project to provision

The current chess project is:

```text
https://lcbeklcwpbgbgcqnmdjb.supabase.co
```

---

## Step 2 — Create the `matches` Table

In your Supabase project, go to **SQL Editor** and run this:

```sql
CREATE TABLE matches (
  match_key  TEXT         PRIMARY KEY,
  data       JSONB        NOT NULL,
  updated_at TIMESTAMPTZ  DEFAULT NOW()
);

-- Allow public read/write (fine for an internal tournament app)
ALTER TABLE matches ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public_all" ON matches
  FOR ALL USING (true) WITH CHECK (true);
```

Click **Run**. You should see `Success. No rows returned.`

---

## Step 3 — Get Your API Keys

In your Supabase project go to:
**Project Settings → API**

Copy:
- **Project URL** — looks like `https://abcdefghij.supabase.co`
- **anon / public key** — a long JWT string starting with `eyJ...`

> ⚠️ Use the **anon/public** key — NOT the `service_role` or `secret` key.

---

## Step 4 — Add Secrets to Streamlit Community Cloud

1. Go to your app on [share.streamlit.io](https://share.streamlit.io)
2. Click **⋮ (three dots) → Settings → Secrets**
3. Paste the following, replacing the placeholder values:

```toml
[supabase]
url = "https://YOUR_PROJECT_REF.supabase.co"
key = "YOUR_ANON_PUBLIC_KEY"
```

4. Click **Save** — the app will automatically restart

---

## Step 5 — For Local Development

Create `.streamlit/secrets.toml` in this folder with the same content:

```toml
[supabase]
url = "https://YOUR_PROJECT_REF.supabase.co"
key = "YOUR_ANON_PUBLIC_KEY"
```

This file is already in `.gitignore` so it will never be committed to GitHub.

---

## How It Works

| Action | What happens |
|---|---|
| App loads | Fetches all match rows fresh from Supabase |
| Save button clicked | Upserts only the changed match row to Supabase |
| Supabase unreachable | Falls back to local `matches_data.json` with a warning |
| Multiple users open | All see the same live data — no conflicts |
