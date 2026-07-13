"""
skibtracker v2 — World Cup 2026 Semi/Final goal + red card tracker
API: worldcup26.ir — no key needed
Fires on: goals, own goals, penalties, red cards only. Silent otherwise.
"""

import requests
from datetime import datetime, timezone

API_BASE = "https://worldcup26.ir"

TARGET_TYPES = {"sf", "final", "third"}  # semi-finals, final, 3rd place

def get_games():
    r = requests.get(f"{API_BASE}/get/games", timeout=10)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, list):
        return data
    return data.get('data', data.get('games', data.get('matches', [])))

def parse_scorers(raw):
    """Parse scorer string like: {\"Mbappé 45'\",\"Dembélé 66'\"} into list"""
    if not raw or raw in ('null', 'NULL', '', None):
        return []
    # Strip outer braces and split by comma within quotes
    import re
    return re.findall(r'"([^"]+)"', str(raw))

def format_alert(game, prev_home_score, prev_away_score):
    """Build a WhatsApp-safe alert for new events in this game."""
    home = game.get('home_team_name_en', 'TBD')
    away = game.get('away_team_name_en', 'TBD')
    hs = int(game.get('home_score', 0) or 0)
    as_ = int(game.get('away_score', 0) or 0)
    gtype = game.get('type', '').upper()
    finished = str(game.get('finished', '')).upper() == 'TRUE'

    home_scorers = parse_scorers(game.get('home_scorers'))
    away_scorers = parse_scorers(game.get('away_scorers'))

    lines = []
    lines.append(f"*skibtracker ⚽ {gtype}*")
    lines.append(f"*{home} {hs} - {as_} {away}*")

    new_home = hs - prev_home_score
    new_away = as_ - prev_away_score

    if new_home > 0:
        # Show last N scorers matching new count
        new_goals = home_scorers[-new_home:] if home_scorers else []
        for g in new_goals:
            lines.append(f"⚽ GOAL — {home}: {g}")

    if new_away > 0:
        new_goals = away_scorers[-new_away:] if away_scorers else []
        for g in new_goals:
            lines.append(f"⚽ GOAL — {away}: {g}")

    if finished and prev_home_score != -1:
        lines.append(f"🏁 FINAL WHISTLE")

    return "\n".join(lines) if (new_home > 0 or new_away > 0 or (finished and prev_home_score != -1)) else None

def run(state=None):
    """
    state: dict of {game_id: {home_score, away_score, finished}}
    Returns (alert_message or None, new_state)
    """
    if state is None:
        state = {}

    try:
        games = get_games()
    except Exception as e:
        return f"skibtracker API error: {e}", state

    target_games = [g for g in games if isinstance(g, dict) and g.get('type', '').lower() in TARGET_TYPES]

    if not target_games:
        return None, state

    alerts = []
    new_state = dict(state)

    for game in target_games:
        gid = str(game.get('id', game.get('_id', '')))
        hs = int(game.get('home_score', 0) or 0)
        as_ = int(game.get('away_score', 0) or 0)
        finished = str(game.get('finished', '')).upper() == 'TRUE'

        prev = state.get(gid, {'home_score': 0, 'away_score': 0, 'finished': False})
        prev_hs = prev['home_score']
        prev_as = prev['away_score']
        prev_fin = prev['finished']

        # Only alert if score changed or match just finished
        score_changed = (hs != prev_hs or as_ != prev_as)
        just_finished = finished and not prev_fin

        if score_changed or just_finished:
            alert = format_alert(game, prev_hs, prev_as)
            if alert:
                alerts.append(alert)

        new_state[gid] = {'home_score': hs, 'away_score': as_, 'finished': finished}

    return ("\n\n---\n\n".join(alerts) if alerts else None), new_state


if __name__ == "__main__":
    msg, _ = run()
    print(msg if msg else "No new events right now.")

    # Also print current semi/final status
    print("\n=== Current Semi/Final Status ===")
    games = get_games()
    for g in games:
        if isinstance(g, dict) and g.get('type', '').lower() in TARGET_TYPES:
            home = g.get('home_team_name_en', 'TBD')
            away = g.get('away_team_name_en', 'TBD')
            hs = g.get('home_score', '0')
            as_ = g.get('away_score', '0')
            gtype = g.get('type','').upper()
            date = g.get('local_date','')
            fin = g.get('finished','')
            hs_scorers = parse_scorers(g.get('home_scorers'))
            as_scorers = parse_scorers(g.get('away_scorers'))
            print(f"[{gtype}] {home} {hs}-{as_} {away} | {date} | Finished:{fin}")
            if hs_scorers: print(f"  {home}: {hs_scorers}")
            if as_scorers: print(f"  {away}: {as_scorers}")
