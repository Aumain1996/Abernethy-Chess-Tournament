import streamlit as st
import pandas as pd
import math
import random
import json
import os
import base64
from datetime import datetime, time
from supabase import create_client

# ─── App Configuration ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="Abernethy Road Chess Tournament",
    page_icon="♟️",
    layout="wide",
)

# ─── Player Data (placeholder list inherited from the table tennis app) ───
PLAYERS = [
    "Trish Mason",
    "Austin Main",
    "Mervin Say",
    "Helen Maurice-jones",
    "Belinda Rogers",
    "Nathan Letizia",
    "Mehraab Patalwala",
    "Sardar Ali",
    "David Chadinha",
    "Lee Oldham",
    "Campbell Burt",
    "Stephen Pope",
    "Tom Howard",
    "Jeronimo Mottin",
    "Aliakbar Boroujerdi",
    "Joshua Perin",
    "Kunal Rao",
    "Joshua Lister",
    "Tim Arthur",
    "Karl Ferris",
    "Dylan Gill",
    "Finlie Orton",
    "Dorothee Dangin",
    "Rowan Florence",
    "Miles Page",
    "Stache Jarosz",
    "Aaron Mitchell",
    "Tabish Ahmad",
    "Rene Van der werf",
    "Fan Zhang",
    "Zhou Yunfei",
    "Colin Kang",
    "Andrew Bostock",
    "James Gardner",
    "Matt Ghiji",
    "Manu Nair",
    "Bienvenido Veloso",
    "Harry Flanagan-dorbin",
    "Jeffrey Ofiana",
    "Peter Baskovich",
    "Elodie Rousset",
    "Abdellah Shafieian dastjerdi",
    "Heer Gudka",
    "Rhys Lenegan",
    "Deepak Maru",
    "Giuseppe Casillo",
    "Amit Jaiswal",
    "Susanne Hantos",
    "Tijana La bianca",
    "Beatriz Padilla quintero",
    "Stephan Burger",
    "Brady Sloane",
    "Jaxon Damiani",
    "Johan van Dyk",
    "Nick Notis",
    "James McEwan",
]


# ─── Helper Functions ────────────────────────────────────────────────────────
def load_players():
    """Return the embedded player list."""
    return PLAYERS.copy()


def get_next_power_of_2(n):
    """Return the next power of 2 >= n."""
    return 2 ** math.ceil(math.log2(n))


def generate_bracket(players):
    """Generate a randomised knockout bracket with byes evenly distributed across both halves."""
    n = len(players)
    bracket_size = get_next_power_of_2(n)
    num_byes = bracket_size - n
    num_rounds = int(math.log2(bracket_size))

    # Shuffle players with a fixed seed so the draw is random but consistent
    random.seed(42)
    shuffled = players.copy()
    random.shuffle(shuffled)

    # Split byes evenly across both halves of the draw
    byes_per_half = num_byes // 2
    byes_left_over = num_byes % 2  # handle odd number of byes

    # Number of matches per half in round 1
    matches_per_half = bracket_size // 4  # e.g. 64/4 = 16 matches per half

    # Players who get a bye (first in the shuffled list)
    bye_players_left = shuffled[:byes_per_half]
    bye_players_right = shuffled[byes_per_half:byes_per_half * 2 + byes_left_over]
    # Remaining players play actual matches
    match_players = shuffled[num_byes:]

    # Split match players evenly across left and right halves
    players_per_half = len(match_players) // 2
    match_players_left = match_players[:players_per_half]
    match_players_right = match_players[players_per_half:]

    # Build the bracket array:
    # Each half: BYE matches FIRST (at the top), then real matches
    bracket = []

    # --- Left half (first 32 positions) ---
    # Bye matches first: player vs BYE
    for p in bye_players_left:
        bracket.append(p)
        bracket.append("BYE")
    # Real matches: player vs player (pairs)
    for i in range(0, len(match_players_left), 2):
        bracket.append(match_players_left[i])
        bracket.append(match_players_left[i + 1])

    # --- Right half (last 32 positions) ---
    # Bye matches first: player vs BYE
    for p in bye_players_right:
        bracket.append(p)
        bracket.append("BYE")
    # Real matches: player vs player (pairs)
    for i in range(0, len(match_players_right), 2):
        bracket.append(match_players_right[i])
        bracket.append(match_players_right[i + 1])

    return bracket, bracket_size, num_rounds


MATCHES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "matches_data.json")


@st.cache_resource
def get_supabase_client():
    """Get a cached Supabase client. Returns None if secrets are not configured."""
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        client = create_client(url, key)
        # Verify connection with a lightweight ping
        client.table("matches").select("match_key").limit(1).execute()
        return client
    except KeyError:
        return None  # Secrets not configured
    except Exception:
        return None  # Connection failed


def load_matches() -> dict:
    """Load all match data from Supabase. Falls back to local JSON file if not configured."""
    client = get_supabase_client()
    if client:
        try:
            response = client.table("matches").select("match_key, data").execute()
            return {row["match_key"]: row["data"] for row in response.data}
        except Exception as e:
            st.error(f"❌ Supabase load failed: {e}")
    # Fallback: local JSON file
    if os.path.exists(MATCHES_PATH):
        try:
            with open(MATCHES_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_matches(matches: dict, changed_key: str = None):
    """Upsert the changed match row to Supabase. Falls back to local JSON if not configured."""
    client = get_supabase_client()
    if client:
        try:
            if changed_key and changed_key in matches:
                client.table("matches").upsert(
                    {"match_key": changed_key, "data": matches[changed_key]}
                ).execute()
            else:
                rows = [{"match_key": k, "data": v} for k, v in matches.items()]
                if rows:
                    client.table("matches").upsert(rows).execute()
            return  # ✅ saved to Supabase — do NOT fall through to file
        except Exception as e:
            st.error(f"❌ Supabase save failed: {e}")
    # Fallback: local JSON file (only reached if Supabase is unavailable)
    try:
        with open(MATCHES_PATH, "w") as f:
            json.dump(matches, f, indent=2)
        st.warning("⚠️ Saved to local file only — Supabase is not connected.")
    except IOError as e:
        st.error(f"❌ Local file save also failed: {e}")


def get_match_key(round_num, match_num):
    """Generate a unique key for a match."""
    return f"R{round_num}_M{match_num}"


def get_round_name(round_num, total_rounds):
    """Get a human-readable name for a round."""
    rounds_remaining = total_rounds - round_num - 1  # 0 = this is the final round
    if rounds_remaining == 0:
        return "🏆 Grand Final"
    elif rounds_remaining == 1:
        return "Semi Finals"
    elif rounds_remaining == 2:
        return "Quarter Finals"
    elif rounds_remaining == 3:
        return "Round of 16"
    else:
        return f"Round {round_num + 1}"


def determine_set_winner(score_a, score_b):
    """Determine if a set has a valid winner (first to 11, win by 2 at 10-10)."""
    if score_a is None or score_b is None:
        return None
    if score_a >= 11 and score_a - score_b >= 2:
        return "A"
    if score_b >= 11 and score_b - score_a >= 2:
        return "B"
    if score_a >= 10 and score_b >= 10:
        if abs(score_a - score_b) >= 2:
            return "A" if score_a > score_b else "B"
    return None


def determine_match_winner(sets_data, forfeit=None):
    """Determine the match winner based on best of 3 sets, or forfeit."""
    if forfeit == "A":
        return "B"  # Player A forfeited → Player B wins
    if forfeit == "B":
        return "A"  # Player B forfeited → Player A wins
    wins_a = 0
    wins_b = 0
    for s in sets_data:
        winner = determine_set_winner(s.get("score_a"), s.get("score_b"))
        if winner == "A":
            wins_a += 1
        elif winner == "B":
            wins_b += 1
    if wins_a >= 2:
        return "A"
    elif wins_b >= 2:
        return "B"
    return None


def get_match_participants(round_num, match_num, bracket, matches, num_rounds):
    """Recursively determine who plays in a given match."""
    if round_num == 0:
        # First round - read directly from bracket
        idx_a = match_num * 2
        idx_b = match_num * 2 + 1
        player_a = bracket[idx_a] if idx_a < len(bracket) else "BYE"
        player_b = bracket[idx_b] if idx_b < len(bracket) else "BYE"
        return player_a, player_b
    else:
        # Later rounds - get winners from previous round
        prev_match_a = match_num * 2
        prev_match_b = match_num * 2 + 1

        player_a = get_winner(round_num - 1, prev_match_a, bracket, matches, num_rounds)
        player_b = get_winner(round_num - 1, prev_match_b, bracket, matches, num_rounds)

        return player_a, player_b


def get_winner(round_num, match_num, bracket, matches, num_rounds):
    """Get the winner of a specific match."""
    player_a, player_b = get_match_participants(round_num, match_num, bracket, matches, num_rounds)

    # Handle byes
    if player_a == "BYE":
        return player_b
    if player_b == "BYE":
        return player_a

    # Check if match has been played
    match_key = get_match_key(round_num, match_num)
    if match_key in matches:
        match_data = matches[match_key]
        sets_data = match_data.get("sets", [])
        forfeit = match_data.get("forfeit")  # "A" or "B" or None
        winner = determine_match_winner(sets_data, forfeit=forfeit)
        if winner == "A":
            return player_a
        elif winner == "B":
            return player_b

    return None


def calculate_ladder(bracket, matches, num_rounds):
    """Calculate the ladder with percentage points for each player."""
    players = [p for p in bracket if p != "BYE"]
    stats = {p: {"played": 0, "sets_won": 0, "sets_lost": 0,
                 "points_won": 0, "points_lost": 0, "matches_won": 0,
                 "matches_lost": 0} for p in players}

    for match_key, match_data in matches.items():
        parts = match_key.split("_")
        round_num = int(parts[0][1:])
        match_num = int(parts[1][1:])

        player_a, player_b = get_match_participants(round_num, match_num, bracket, matches, num_rounds)

        if player_a == "BYE" or player_b == "BYE" or player_a is None or player_b is None:
            continue

        sets_data = match_data.get("sets", [])
        match_winner = determine_match_winner(sets_data)

        if match_winner is None:
            continue

        stats[player_a]["played"] += 1
        stats[player_b]["played"] += 1

        if match_winner == "A":
            stats[player_a]["matches_won"] += 1
            stats[player_b]["matches_lost"] += 1
        else:
            stats[player_b]["matches_won"] += 1
            stats[player_a]["matches_lost"] += 1

        for s in sets_data:
            sa = s.get("score_a", 0) or 0
            sb = s.get("score_b", 0) or 0
            stats[player_a]["points_won"] += sa
            stats[player_a]["points_lost"] += sb
            stats[player_b]["points_won"] += sb
            stats[player_b]["points_lost"] += sa

            set_winner = determine_set_winner(sa, sb)
            if set_winner == "A":
                stats[player_a]["sets_won"] += 1
                stats[player_b]["sets_lost"] += 1
            elif set_winner == "B":
                stats[player_b]["sets_won"] += 1
                stats[player_a]["sets_lost"] += 1

    return stats


# ─── Load Data ───────────────────────────────────────────────────────────────
players = load_players()
bracket, bracket_size, num_rounds = generate_bracket(players)
matches = load_matches()

# ─── Sidebar Navigation ──────────────────────────────────────────────────────
st.sidebar.title("♟️ Navigation")
page = st.sidebar.radio(
    "Go to:",
    ["🎯 Draw", "📝 Results Entry", "📊 Ladder", "📋 Rules of the Tournament"]
)

st.title("♟️ Abernethy Road Chess Tournament")
st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1: GRAPHICAL DRAW
# ═══════════════════════════════════════════════════════════════════════════════
if page == "🎯 Draw":
    st.header("🎯 Tournament Draw")
    st.markdown("Visual knockout bracket — left side and right side converge to the **Grand Final** in the centre.")

    # Build bracket data for each round
    def get_bracket_display_data():
        """Build display names for every slot in the bracket."""
        rounds_data = []
        for r in range(num_rounds):
            num_matches = bracket_size // (2 ** (r + 1))
            round_matches = []
            for m in range(num_matches):
                pa, pb = get_match_participants(r, m, bracket, matches, num_rounds)
                w = get_winner(r, m, bracket, matches, num_rounds)
                round_matches.append({"player_a": pa, "player_b": pb, "winner": w})
            rounds_data.append(round_matches)
        return rounds_data

    rounds_data = get_bracket_display_data()

    # Split bracket into two halves (top half = left side, bottom half = right side)
    half = bracket_size // 2  # 32 players per side

    def get_display_name(name):
        if name is None:
            return "TBD"
        if name == "BYE":
            return "BYE"
        # Truncate long names
        return name if len(name) <= 22 else name[:20] + "…"

    def build_bracket_html():
        """Generate HTML/CSS for a graphical bracket view."""

        # Load and base64-encode the trophy image for embedding in HTML
        trophy_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Table Tennis Trophy.jpg")
        trophy_img_tag = ""
        if os.path.exists(trophy_path):
            with open(trophy_path, "rb") as f:
                trophy_b64 = base64.b64encode(f.read()).decode()
            trophy_img_tag = (
                f'<img src="data:image/jpeg;base64,{trophy_b64}" '
                f'style="width:120px;height:auto;display:block;margin:0 auto 10px auto;'
                f'border-radius:8px;opacity:0.95;" alt="Trophy"/>'
            )        # Determine rounds per side (all rounds except final)
        rounds_per_side = num_rounds - 1  # e.g. 5 rounds per side, then 1 final

        # Split matches into left and right halves
        left_rounds = []
        right_rounds = []
        for r in range(rounds_per_side):
            num_matches = len(rounds_data[r])
            half_count = num_matches // 2
            left_rounds.append(rounds_data[r][:half_count])
            right_rounds.append(rounds_data[r][half_count:])

        # Final match
        final_match = rounds_data[num_rounds - 1][0] if rounds_data[num_rounds - 1] else None

        # CSS styles
        css = """
        <style>
            .bracket-container {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 11px;
                overflow-x: auto;
                padding: 20px 0;
            }
            .bracket-side {
                display: flex;
                align-items: center;
            }
            .bracket-round {
                display: flex;
                flex-direction: column;
                justify-content: center;
                margin: 0 2px;
            }
            .bracket-match {
                display: flex;
                flex-direction: column;
                margin: 4px 0;
                border: 1px solid #444;
                border-radius: 4px;
                overflow: hidden;
                min-width: 140px;
                background: #1e1e1e;
            }
            .bracket-player {
                padding: 4px 8px;
                border-bottom: 1px solid #333;
                white-space: nowrap;
                color: #ddd;
            }
            .bracket-player:last-child {
                border-bottom: none;
            }
            .bracket-player.winner {
                background: #1a5c2a;
                font-weight: bold;
                color: #4cff72;
            }
            .bracket-player.bye {
                color: #666;
                font-style: italic;
            }
            .bracket-player.tbd {
                color: #888;
                font-style: italic;
            }
            .final-container {
                display: flex;
                flex-direction: column;
                align-items: center;
                margin: 0 15px;
                min-width: 170px;
            }
            .final-label {
                font-size: 14px;
                font-weight: bold;
                color: #ffd700;
                margin-bottom: 8px;
                text-align: center;
            }
            .final-match {
                border: 2px solid #ffd700;
                border-radius: 6px;
                overflow: hidden;
                min-width: 170px;
                background: #2a2a1a;
            }
            .final-match .bracket-player {
                padding: 6px 10px;
                font-size: 12px;
            }
            .final-match .bracket-player.winner {
                background: #3d6b1e;
                color: #7dff3a;
            }
            .champion-label {
                margin-top: 10px;
                font-size: 13px;
                color: #ffd700;
                font-weight: bold;
                text-align: center;
            }
            .round-label {
                text-align: center;
                font-size: 10px;
                color: #999;
                margin-bottom: 6px;
                font-weight: bold;
                text-transform: uppercase;
            }
        </style>
        """

        def render_match(match_data):
            pa = get_display_name(match_data["player_a"])
            pb = get_display_name(match_data["player_b"])
            w = match_data["winner"]

            class_a = ""
            class_b = ""
            if pa == "BYE":
                class_a = " bye"
            elif pa == "TBD":
                class_a = " tbd"
            if pb == "BYE":
                class_b = " bye"
            elif pb == "TBD":
                class_b = " tbd"

            if w is not None:
                if w == match_data["player_a"]:
                    class_a = " winner"
                elif w == match_data["player_b"]:
                    class_b = " winner"

            return f'''<div class="bracket-match">
                <div class="bracket-player{class_a}">{pa}</div>
                <div class="bracket-player{class_b}">{pb}</div>
            </div>'''

        def render_round(round_matches):
            html = '<div class="bracket-round">'
            for match in round_matches:
                html += render_match(match)
            html += '</div>'
            return html

        # Build left side (rounds go left to right, converging to center)
        left_html = '<div class="bracket-side">'
        for r in range(rounds_per_side):
            left_html += render_round(left_rounds[r])
        left_html += '</div>'

        # Build right side (rounds go right to left, converging to center)
        right_html = '<div class="bracket-side">'
        for r in range(rounds_per_side - 1, -1, -1):
            right_html += render_round(right_rounds[r])
        right_html += '</div>'

        # Build final
        final_html = '<div class="final-container">'
        final_html += trophy_img_tag
        final_html += '<div class="final-label">🏆 GRAND FINAL 🏆</div>'
        if final_match:
            pa = get_display_name(final_match["player_a"])
            pb = get_display_name(final_match["player_b"])
            w = final_match["winner"]
            class_a = " tbd" if pa == "TBD" else ""
            class_b = " tbd" if pb == "TBD" else ""
            if w is not None:
                if w == final_match["player_a"]:
                    class_a = " winner"
                elif w == final_match["player_b"]:
                    class_b = " winner"

            final_html += f'''<div class="final-match">
                <div class="bracket-player{class_a}">{pa}</div>
                <div class="bracket-player{class_b}">{pb}</div>
            </div>'''
            if w:
                final_html += f'<div class="champion-label">🥇 {get_display_name(w)}</div>'
        final_html += '</div>'

        full_html = f"""
        {css}
        <div class="bracket-container">
            {left_html}
            {final_html}
            {right_html}
        </div>
        """
        return full_html

    # Calculate height based on number of first-round matches
    first_round_matches = bracket_size // 2
    estimated_height = max(800, (first_round_matches // 2) * 58 + 100)

    bracket_html = build_bracket_html()
    st.components.v1.html(bracket_html, height=estimated_height, scrolling=True)

    # Also show a simplified text-based bracket for clarity
    st.markdown("---")
    st.markdown("### 📋 Round-by-Round Summary")
    for r in range(num_rounds):
        round_name = get_round_name(r, num_rounds)
        with st.expander(f"**{round_name}** ({len(rounds_data[r])} matches)", expanded=False):
            summary = []
            for m, md in enumerate(rounds_data[r]):
                pa = md["player_a"] or "TBD"
                pb = md["player_b"] or "TBD"
                w = md["winner"]
                if pa == "BYE":
                    summary.append({"#": m+1, "Player A": "—", "Player B": pb, "Result": f"{pb} (BYE)"})
                elif pb == "BYE":
                    summary.append({"#": m+1, "Player A": pa, "Player B": "—", "Result": f"{pa} (BYE)"})
                else:
                    summary.append({"#": m+1, "Player A": pa, "Player B": pb, "Result": w or "—"})
            st.dataframe(pd.DataFrame(summary), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 2: RESULTS ENTRY
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📝 Results Entry":
    st.header("📝 Results Entry")
    st.markdown(f"**{len(players)} Players** | **{num_rounds} Rounds** | Best of 3 Sets (First to 11)")

    # Round selector
    round_names = [get_round_name(r, num_rounds) for r in range(num_rounds)]
    selected_round = st.selectbox("Select Round", range(num_rounds),
                                   format_func=lambda x: round_names[x])

    num_matches_in_round = bracket_size // (2 ** (selected_round + 1))

    # Count real (non-bye) matches for the header
    real_matches = [
        m for m in range(num_matches_in_round)
        if not any(
            p == "BYE"
            for p in get_match_participants(selected_round, m, bracket, matches, num_rounds)
        )
    ]
    st.markdown(f"### {round_names[selected_round]} — {len(real_matches)} Match(es)")
    st.markdown("---")

    match_display_num = 0
    for match_idx in range(num_matches_in_round):
        player_a, player_b = get_match_participants(selected_round, match_idx, bracket, matches, num_rounds)

        # Skip BYE matches entirely — they don't need results entered
        if player_a == "BYE" or player_b == "BYE":
            continue

        if player_a is None or player_b is None:
            st.markdown(f"*Waiting for previous round results*")
            st.markdown("---")
            continue

        match_display_num += 1
        match_key = get_match_key(selected_round, match_idx)
        match_data = matches.get(match_key, {})

        winner = get_winner(selected_round, match_idx, bracket, matches, num_rounds)
        is_forfeit = bool(match_data.get("forfeit"))
        forfeit_label = f" — 🚫 Forfeit ({match_data.get('forfeit_player', '')})" if is_forfeit else ""

        with st.expander(f"**Match {match_display_num}: {player_a} vs {player_b}**" +
                         (f" — Winner: {winner} 🏆{forfeit_label}" if winner else ""), expanded=False):

            match_date = st.date_input(
                    "Match Date",
                    value=datetime.strptime(match_data["date"], "%Y-%m-%d").date()
                    if match_data.get("date") else None,
                    key=f"date_{match_key}"
                )

            # ── Forfeit toggle ────────────────────────────────────────────────
            st.markdown("---")
            forfeit_checked = st.checkbox(
                "🚫 Record as Forfeit (opponent did not show up)",
                value=is_forfeit,
                key=f"forfeit_check_{match_key}"
            )

            forfeit_player = None
            if forfeit_checked:
                forfeiting = st.radio(
                    "Which player forfeited?",
                    options=[player_a, player_b],
                    index=0 if match_data.get("forfeit") != "B" else 1,
                    key=f"forfeit_who_{match_key}"
                )
                forfeit_player = "A" if forfeiting == player_a else "B"
                st.warning(f"⚠️ **{forfeiting}** will be recorded as forfeiting. "
                           f"**{''.join([player_b if forfeiting == player_a else player_a])}** advances.")

            # ── Score entry (hidden when forfeit is selected) ─────────────────
            new_sets = match_data.get("sets", [{}, {}, {}])
            while len(new_sets) < 3:
                new_sets.append({})

            if not forfeit_checked:
                st.markdown("---")
                st.markdown(f"**{player_a}** vs **{player_b}**")
                new_sets = []
                cols = st.columns(3)
                sets_data = match_data.get("sets", [{}, {}, {}])
                while len(sets_data) < 3:
                    sets_data.append({})
                for set_idx in range(3):
                    with cols[set_idx]:
                        st.markdown(f"**Set {set_idx + 1}**")
                        sa = st.number_input(
                            f"{player_a}",
                            min_value=0, max_value=99,
                            value=sets_data[set_idx].get("score_a", 0) or 0,
                            key=f"sa_{match_key}_{set_idx}"
                        )
                        sb = st.number_input(
                            f"{player_b}",
                            min_value=0, max_value=99,
                            value=sets_data[set_idx].get("score_b", 0) or 0,
                            key=f"sb_{match_key}_{set_idx}"
                        )
                        new_sets.append({"score_a": sa, "score_b": sb})

                        sw = determine_set_winner(sa, sb)
                        if sw == "A":
                            st.success(f"✓ {player_a}")
                        elif sw == "B":
                            st.success(f"✓ {player_b}")

            # ── Save button ───────────────────────────────────────────────────
            st.markdown("---")
            if st.button(f"💾 Save Match {match_display_num}", key=f"save_{match_key}"):
                matches[match_key] = {
                    "player_a": player_a,
                    "player_b": player_b,
                    "date": match_date.strftime("%Y-%m-%d") if match_date else None,
                    "sets": new_sets,
                    "forfeit": forfeit_player,
                    "forfeit_player": (player_a if forfeit_player == "A" else player_b) if forfeit_player else None,
                }
                save_matches(matches, changed_key=match_key)
                st.success("✅ Match saved successfully!")
                st.rerun()

        st.markdown("---")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 3: LADDER
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Ladder":
    st.header("📊 Tournament Ladder")
    st.markdown("Rankings based on match results. **Percentage** = Points Won / Total Points Played × 100")

    stats = calculate_ladder(bracket, matches, num_rounds)

    ladder_data = []
    for player, s in stats.items():
        total_points = s["points_won"] + s["points_lost"]
        pct = (s["points_won"] / total_points * 100) if total_points > 0 else 0.0
        ladder_data.append({
            "Player": player,
            "Matches Played": s["played"],
            "Matches Won": s["matches_won"],
            "Matches Lost": s["matches_lost"],
            "Sets Won": s["sets_won"],
            "Sets Lost": s["sets_lost"],
            "Points Won": s["points_won"],
            "Points Lost": s["points_lost"],
            "Percentage (%)": round(pct, 1)
        })

    df_ladder = pd.DataFrame(ladder_data)
    df_ladder = df_ladder.sort_values(
        by=["Matches Won", "Percentage (%)"],
        ascending=[False, False]
    ).reset_index(drop=True)
    df_ladder.index += 1
    df_ladder.index.name = "Rank"

    st.dataframe(df_ladder, use_container_width=True)

    # Highlight top performers
    if not df_ladder.empty and df_ladder["Matches Played"].sum() > 0:
        st.markdown("### 🌟 Top Performers")
        top_3 = df_ladder.head(3)
        cols = st.columns(3)
        medals = ["🥇", "🥈", "🥉"]
        for i, (_, row) in enumerate(top_3.iterrows()):
            if i < 3 and row["Matches Played"] > 0:
                with cols[i]:
                    st.metric(
                        label=f"{medals[i]} {row['Player']}",
                        value=f"{row['Percentage (%)']}%",
                        delta=f"{row['Matches Won']}W - {row['Matches Lost']}L"
                    )


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 4: RULES
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Rules of the Tournament":
    st.header("📋 Rules of the Tournament")

    st.markdown("""
    ## 🏓 Abernethy Road Table Tennis Tournament Rules

    ### Format
    - **Single Elimination Knockout** tournament
    - All matches are **Best of 3 Sets**
    - Each set is played to **11 points**
    - If the score reaches **10-10**, a player must win by **2 clear points** (deuce rule)
    - The first player to win **2 sets** wins the match and advances to the next round

    ---

    ### Match Rules
    1. At the **start of each set**, a **"play for serve"** point is played — whoever wins it earns the first serve. This point does **not** count towards the set score
    2. After each point, the **winner of that point earns the serve** for the next point
    3. Players do **not** have to serve cross court
    4. A serve must **bounce once on each side** of the table
    5. **Let serves** (net on serve, lands correctly) are replayed
    6. A point is won when the opponent **fails to make a legal return**
    7. At **10-10 (deuce)**, the same serving rule applies — winner of each point gets the next serve
    8. Players switch ends after each set
    9. If there is a **disputed call**, the tournament organiser's decision is final

    ---

    ### Tournament Structure
    - **56 players** entered in a knockout bracket
    - Players receiving a **BYE** automatically advance to the next round
    - All rounds must be completed before the next round begins
    - The draw is fixed at the start of the tournament

    ---

    ### Code of Conduct
    1. **Respect** — Excessive celebration will be tolerated and is encouraged
    2. **Sportsmanship** — Shake hands after each match

    ---

    ### Scoring & Ladder
    - The **Ladder** page tracks each player's overall performance
    - **Percentage** is calculated as: `Points Won ÷ Total Points × 100`
    - This gives a measure of overall dominance across all matches played

    ---

    ### Contact
    For any queries regarding the tournament, please contact Austin.

    ---

    *Good luck and may the superior Abernethy road human win!* 🏆
    """)

# ─── Footer ──────────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("**Abernethy Road Chess Tournament**")
st.sidebar.markdown(f"👥 {len(players)} Players Registered")
st.sidebar.markdown(f"🗓️ Season 2026")
