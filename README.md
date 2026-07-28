# Abernethy Road Chess Tournament

A Streamlit app scaffold for running the Abernethy Road Chess Tournament. It is based on the existing table tennis tournament architecture and will be adapted once the chess tournament format, rules, and player list are finalised.

## What the app does

- Displays the full knockout bracket, including first-round byes
- Uses a fixed random seed so the draw remains consistent between sessions
- Lets organisers enter a match date and result details
- Provides a starting point for chess-specific result validation
- Supports recording forfeits
- Automatically advances winners into later rounds
- Shows a round-by-round summary and highlights the tournament champion
- Builds a live ladder with tournament statistics
- Includes the tournament format, match rules, and code of conduct

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

- `streamlit_app.py` — application UI, bracket logic, scoring, and persistence
- `requirements.txt` — Python dependencies
- `Abernethy Rd Table Tennis Comp Registrations.csv` — retained source data from the original app until chess registrations are supplied
- `Table Tennis Trophy.jpg` — retained placeholder image until chess artwork is supplied

The current player list and detailed match-entry logic are placeholders inherited from the table tennis app. Replace them with the chess tournament details before launch.
