# Abernethy Road Chess Tournament

A Streamlit app for running the Abernethy Road Chess Tournament. It uses the same lightweight architecture as the table tennis tournament app, adapted for a self-managed 10-minute-per-player knockout chess competition.

## What the app does

- Opens on the tournament rules and app instructions page
- Displays the full knockout bracket, including first-round byes
- Uses a fixed random seed so the draw remains consistent between sessions
- Pairs similar signup responses together where possible in the first round
- Lets organisers enter a match date, winner, and result method
- Supports checkmate, time forfeit, resignation, opponent forfeit, and other result types
- Automatically advances winners into later rounds
- Shows a round-by-round summary and highlights the tournament champion
- Includes 10-minute clock rules and app usage instructions

Match results are stored in Supabase when it is configured. If Supabase is unavailable, the app falls back to a local `matches_data.json` file.

## Run locally

1. Create and activate a Python virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Start the app:

   ```bash
   streamlit run streamlit_app.py
   ```

Streamlit will print the local address to open in a browser.

## Optional Supabase setup

To share results across deployments and users, create a Supabase table named `matches` with:

- `match_key`: text, primary key
- `data`: JSON/JSONB

Then add `.streamlit/secrets.toml`:

```toml
[supabase]
url = "https://your-project.supabase.co"
key = "your-supabase-key"
```

Do not commit real credentials to the repository. Without these settings, results are saved locally instead.

## Project files

- `streamlit_app.py` — application UI, bracket logic, result entry, and persistence
- `requirements.txt` — Python dependencies
- `chess_players.csv` — chess signup list with player names and responses
- `matches_data.json` — local fallback store when Supabase is not connected

The app expects `chess_players.csv` to contain `Name` and `Response` columns.
