import csv
import json
import math
import os
import random
import re
from datetime import datetime

import pandas as pd
import streamlit as st
from supabase import create_client


st.set_page_config(
    page_title="Abernethy Road Chess Tournament",
    page_icon="♟️",
    layout="wide",
)


TOURNAMENT_NAME = "Abernethy Road Chess Tournament"
SEASON = "2026"
RANDOM_SEED = 2026
ORGANISER_NAME = "Pierre Pouchol"
ORGANISER_EMAIL = "pierre.pouchol@fortescue.com"
MATCHES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "matches_data.json")
PLAYERS_CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chess_players.csv")

# Fallback only. Replace by adding chess_players.csv with name/response columns.
FALLBACK_PLAYERS = [
    {"name": "Player 1", "response": "yes keen"},
    {"name": "Player 2", "response": "yes keen"},
    {"name": "Player 3", "response": "maybe, depending on time"},
    {"name": "Player 4", "response": "maybe, depending on time"},
]


def normalise_response(response: str) -> str:
    text = (response or "").strip().lower()
    words = set(re.findall(r"[a-z]+", text))
    if "yes" in words or "keen" in words or "definitely" in words or "count me" in text:
        return "keen"
    if "maybe" in words or "depending" in words or "depends" in words or "timing" in words or "unsure" in words or "possibly" in words:
        return "maybe"
    if "beginner" in words or "casual" in words or "interested" in words:
        return "casual"
    if "no" in words or "cannot" in words or "unavailable" in words or "can't" in text:
        return "unavailable"
    return "unspecified"


def display_response_group(group: str) -> str:
    return {
        "keen": "Keen",
        "maybe": "Maybe / time dependent",
        "casual": "Beginner / casual",
        "unavailable": "Unavailable",
        "unspecified": "Unspecified",
    }.get(group, "Unspecified")


def load_players():
    """Load chess players from chess_players.csv when present."""
    if not os.path.exists(PLAYERS_CSV_PATH):
        return FALLBACK_PLAYERS

    with open(PLAYERS_CSV_PATH, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        return FALLBACK_PLAYERS

    columns = {c.lower().strip(): c for c in rows[0].keys()}
    name_col = next(
        (columns[c] for c in columns if c in {"name", "player", "full name", "participant"}),
        next(iter(rows[0].keys())),
    )
    response_col = next(
        (columns[c] for c in columns if c in {"response", "answer", "availability", "interest", "comment"}),
        None,
    )

    players = []
    for row in rows:
        name = (row.get(name_col) or "").strip()
        if not name:
            continue
        players.append({"name": name, "response": (row.get(response_col) or "").strip() if response_col else ""})

    return players or FALLBACK_PLAYERS


def get_next_power_of_2(n):
    return 2 ** math.ceil(math.log2(max(n, 2)))


def pair_players_by_response(players):
    """Pair players with similar signup responses before building the bracket."""
    rng = random.Random(RANDOM_SEED)
    grouped = {"keen": [], "maybe": [], "casual": [], "unspecified": [], "unavailable": []}

    for player in players:
        enriched = {**player, "group": normalise_response(player.get("response", ""))}
        grouped.setdefault(enriched["group"], []).append(enriched)

    for group_players in grouped.values():
        rng.shuffle(group_players)

    ordered = []
    leftovers = []
    for group in ["keen", "maybe", "casual", "unspecified", "unavailable"]:
        group_players = grouped.get(group, [])
        while len(group_players) >= 2:
            ordered.extend([group_players.pop(0), group_players.pop(0)])
        if group_players:
            leftovers.append(group_players.pop(0))

    ordered.extend(leftovers)

    return ordered


def generate_bracket(players):
    ordered_players = pair_players_by_response(players)
    bracket_size = get_next_power_of_2(len(ordered_players))
    num_byes = bracket_size - len(ordered_players)
    paired_players = ordered_players[: len(ordered_players) - num_byes]
    bye_players = ordered_players[len(ordered_players) - num_byes :]

    bracket = [p["name"] for p in paired_players]
    for player in bye_players:
        bracket.extend([player["name"], "BYE"])

    return bracket, bracket_size, int(math.log2(bracket_size))


@st.cache_resource
def get_supabase_client():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        client = create_client(url, key)
        client.table("matches").select("match_key").limit(1).execute()
        return client
    except Exception:
        return None


def load_matches() -> dict:
    client = get_supabase_client()
    if client:
        try:
            response = client.table("matches").select("match_key, data").execute()
            return {row["match_key"]: row["data"] for row in response.data}
        except Exception as e:
            st.error(f"Supabase load failed: {e}")

    if os.path.exists(MATCHES_PATH):
        try:
            with open(MATCHES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_matches(matches: dict, changed_key: str = None):
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
            return
        except Exception as e:
            st.error(f"Supabase save failed: {e}")

    try:
        with open(MATCHES_PATH, "w", encoding="utf-8") as f:
            json.dump(matches, f, indent=2)
        st.warning("Saved to local file only because Supabase is not connected.")
    except OSError as e:
        st.error(f"Local file save also failed: {e}")


def round_name(round_num, num_rounds):
    remaining = num_rounds - round_num
    if remaining == 1:
        return "Grand Final"
    if remaining == 2:
        return "Semi Finals"
    if remaining == 3:
        return "Quarter Finals"
    if remaining == 4:
        return "Round of 16"
    return f"Round {round_num + 1}"


def match_key(round_num, match_num):
    return f"R{round_num}_M{match_num}"


def get_match_participants(round_num, match_num, bracket, matches, num_rounds):
    if round_num == 0:
        return bracket[match_num * 2], bracket[match_num * 2 + 1]

    prev_match_a = match_num * 2
    prev_match_b = match_num * 2 + 1
    return (
        get_winner(round_num - 1, prev_match_a, bracket, matches, num_rounds),
        get_winner(round_num - 1, prev_match_b, bracket, matches, num_rounds),
    )


def get_winner(round_num, match_num, bracket, matches, num_rounds):
    player_a, player_b = get_match_participants(round_num, match_num, bracket, matches, num_rounds)
    if player_a == "BYE":
        return player_b
    if player_b == "BYE":
        return player_a
    if not player_a or not player_b:
        return None

    data = matches.get(match_key(round_num, match_num), {})
    winner = data.get("winner")
    return winner if winner in {player_a, player_b} else None


def match_status(round_num, match_num, bracket, matches, num_rounds):
    player_a, player_b = get_match_participants(round_num, match_num, bracket, matches, num_rounds)
    if player_a == "BYE" or player_b == "BYE":
        return "Bye"
    if not player_a or not player_b:
        return "Waiting"
    if get_winner(round_num, match_num, bracket, matches, num_rounds):
        return "Complete"
    return "Pending"


def build_rounds_data(bracket, matches, num_rounds):
    rounds = []
    bracket_size = len(bracket)
    for r in range(num_rounds):
        round_matches = []
        for m in range(bracket_size // (2 ** (r + 1))):
            player_a, player_b = get_match_participants(r, m, bracket, matches, num_rounds)
            round_matches.append(
                {
                    "player_a": player_a,
                    "player_b": player_b,
                    "winner": get_winner(r, m, bracket, matches, num_rounds),
                    "status": match_status(r, m, bracket, matches, num_rounds),
                }
            )
        rounds.append(round_matches)
    return rounds


def css_class_for_match(match):
    if match["status"] == "Complete":
        return "complete"
    if match["status"] == "Bye":
        return "bye"
    if match["status"] == "Waiting":
        return "waiting"
    return "pending"


def build_bracket_html(rounds_data, num_rounds):
    def player_line(name, winner):
        label = name or "TBD"
        safe = str(label).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        cls = "player winner" if winner and label == winner else "player"
        return f'<div class="{cls}">{safe}</div>'

    round_columns = []
    for r, round_matches in enumerate(rounds_data):
        cards = []
        for idx, match in enumerate(round_matches, start=1):
            cls = css_class_for_match(match)
            cards.append(
                f"""
                <div class="match-card {cls}">
                    <div class="match-meta">Match {idx} · {match["status"]}</div>
                    {player_line(match["player_a"], match["winner"])}
                    {player_line(match["player_b"], match["winner"])}
                </div>
                """
            )
        round_columns.append(
            f"""
            <section class="round-column">
                <h3>{round_name(r, num_rounds)}</h3>
                <div class="matches">{''.join(cards)}</div>
            </section>
            """
        )

    return f"""
    <style>
        .bracket-wrap {{
            overflow-x: auto;
            padding: 8px 0 24px;
        }}
        .bracket {{
            display: grid;
            grid-template-columns: repeat({num_rounds}, minmax(210px, 1fr));
            gap: 18px;
            min-width: {max(860, num_rounds * 230)}px;
        }}
        .round-column h3 {{
            margin: 0 0 12px;
            color: #f8fafc;
            font-size: 16px;
            font-weight: 700;
        }}
        .matches {{
            display: flex;
            flex-direction: column;
            gap: 14px;
        }}
        .match-card {{
            border: 1px solid rgba(148, 163, 184, 0.34);
            border-left: 4px solid #64748b;
            border-radius: 8px;
            background: #111827;
            padding: 10px;
            min-height: 98px;
            box-shadow: 0 8px 18px rgba(0, 0, 0, 0.18);
        }}
        .match-card.complete {{ border-left-color: #22c55e; }}
        .match-card.pending {{ border-left-color: #38bdf8; }}
        .match-card.waiting {{ opacity: 0.72; }}
        .match-card.bye {{ border-left-color: #f59e0b; }}
        .match-meta {{
            color: #94a3b8;
            font-size: 12px;
            margin-bottom: 8px;
        }}
        .player {{
            background: #1f2937;
            border-radius: 6px;
            color: #e5e7eb;
            font-size: 14px;
            line-height: 1.25;
            margin-top: 6px;
            min-height: 30px;
            padding: 7px 8px;
            overflow-wrap: anywhere;
        }}
        .player.winner {{
            background: #064e3b;
            color: #dcfce7;
            font-weight: 700;
        }}
    </style>
    <div class="bracket-wrap"><div class="bracket">{''.join(round_columns)}</div></div>
    """


players = load_players()
bracket, bracket_size, num_rounds = generate_bracket(players)
matches = load_matches()
rounds_data = build_rounds_data(bracket, matches, num_rounds)

st.sidebar.title("♟️ Navigation")
page = st.sidebar.radio(
    "Go to:",
    ["📋 Rules of the Tournament", "🎯 Draw", "📝 Results Entry"],
)

st.title(f"♟️ {TOURNAMENT_NAME}")
st.markdown("---")


if page == "📋 Rules of the Tournament":
    st.header("📋 Rules of the Tournament")
    st.markdown(
        """
        Welcome to the Abernethy Road Chess Tournament. This is a self-managed workplace
        knockout competition using a simple **10 minutes per player, no increment** format.

        ### Match Format

        - Each match is one game of chess.
        - Each player has **10 cumulative minutes** for all of their own moves.
        - Start your clock when it is your turn. Stop it after you make your move.
        - If your own clock reaches **0:00**, you lose on time.
        - A checkmate wins immediately, even if time remains on both clocks.
        - Stalemate, agreed draw, threefold repetition, or insufficient mating material should be replayed unless both players agree another practical resolution before starting.
        - If a player makes an illegal move, pause the clock, restore the legal position, and continue. Repeated illegal moves can be referred to the organiser.

        ### Scheduling

        - Pairings are self-managed. Contact your designated opponent and organise a time that works for both of you.
        - Please complete your match promptly so later rounds are not blocked.
        - The chess board and two-player timer will be provided for tournament matches.
        - Use the provided timer so both players clearly track their own 10-minute limit.

        ### Organiser

        - Tournament organiser: **Pierre Pouchol**.
        - Questions, timing issues, disputed results, or rule queries should go to [pierre.pouchol@fortescue.com](mailto:pierre.pouchol@fortescue.com).

        ### App Instructions

        - Use **Draw** to see your opponent and the live knockout bracket.
        - Use **Results Entry** after your match to record the winner.
        - Only enter a result once both players agree the game is complete.
        - Winners automatically flow into the next round of the draw.

        ### Useful Rule References

        - [FIDE Laws of Chess](https://handbook.fide.com/chapter/e012023) for formal chess and clock rules.
        - [US Chess quick/speed chess overview](https://new.uschess.org/speed-and-quick-chess-everybody) for time-control context.

        """
    )

elif page == "🎯 Draw":
    st.header("🎯 Tournament Draw")
    st.markdown(
        "Pairings are seeded from signup responses so similar availability/enthusiasm responses are grouped where possible."
    )

    st.html(build_bracket_html(rounds_data, num_rounds))

    st.markdown("### Round-by-Round Summary")
    for r, round_matches in enumerate(rounds_data):
        with st.expander(f"{round_name(r, num_rounds)} ({len(round_matches)} matches)", expanded=(r == 0)):
            rows = []
            for idx, match in enumerate(round_matches, start=1):
                rows.append(
                    {
                        "Match": idx,
                        "Player A": match["player_a"] or "TBD",
                        "Player B": match["player_b"] or "TBD",
                        "Status": match["status"],
                        "Winner": match["winner"] or "",
                    }
                )
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

elif page == "📝 Results Entry":
    st.header("📝 Results Entry")
    st.markdown("Record one winner per completed chess match. Winners automatically advance.")

    selected_round = st.selectbox(
        "Select Round",
        range(num_rounds),
        format_func=lambda r: round_name(r, num_rounds),
    )

    round_matches = rounds_data[selected_round]
    playable_count = 0

    for match_idx, match in enumerate(round_matches):
        player_a, player_b = match["player_a"], match["player_b"]
        key = match_key(selected_round, match_idx)

        if player_a == "BYE" or player_b == "BYE":
            continue

        match_label = f"Match {match_idx + 1}: {player_a or 'TBD'} vs {player_b or 'TBD'}"
        if not player_a or not player_b:
            with st.expander(match_label, expanded=False):
                st.info("Waiting for previous round results.")
            continue

        playable_count += 1
        existing = matches.get(key, {})
        winner = existing.get("winner")
        expanded = winner is None

        with st.expander(match_label + (f" — Winner: {winner}" if winner else ""), expanded=expanded):
            match_date = st.date_input(
                "Match date",
                value=datetime.strptime(existing.get("date", datetime.now().date().isoformat()), "%Y-%m-%d").date(),
                key=f"date_{key}",
            )
            selected_winner = st.radio(
                "Winner",
                [player_a, player_b],
                index=[player_a, player_b].index(winner) if winner in {player_a, player_b} else 0,
                key=f"winner_{key}",
            )
            result_method = st.selectbox(
                "Result method",
                ["Checkmate", "Time forfeit", "Resignation", "Opponent forfeit", "Other"],
                index=["Checkmate", "Time forfeit", "Resignation", "Opponent forfeit", "Other"].index(
                    existing.get("method", "Checkmate")
                )
                if existing.get("method", "Checkmate") in ["Checkmate", "Time forfeit", "Resignation", "Opponent forfeit", "Other"]
                else 0,
                key=f"method_{key}",
            )
            if st.button(f"Save Match {match_idx + 1}", key=f"save_{key}"):
                matches[key] = {
                    "winner": selected_winner,
                    "loser": player_b if selected_winner == player_a else player_a,
                    "date": match_date.isoformat(),
                    "method": result_method,
                    "updated_at": datetime.now().isoformat(timespec="seconds"),
                }
                save_matches(matches, changed_key=key)
                st.success("Match saved successfully.")
                st.rerun()

    if playable_count == 0:
        st.info("No playable matches are available in this round yet.")


st.sidebar.markdown("---")
st.sidebar.markdown(f"**{TOURNAMENT_NAME}**")
st.sidebar.markdown(f"👥 {len(players)} Players Registered")
st.sidebar.markdown(f"🗓️ Season {SEASON}")
st.sidebar.markdown(f"Organiser: [{ORGANISER_NAME}](mailto:{ORGANISER_EMAIL})")
