import requests
from datetime import datetime, timezone

API_BASE = "https://worldcup26.ir"

# Match IDs for semis + final (based on tournament bracket)
TARGET_MATCHES = {
    "Semi-Final 1": {"date": "2026-07-14", "kickoff_et": "19:00"},
    "Semi-Final 2": {"date": "2026-07-15", "kickoff_et": "19:00"},
    "Final":        {"date": "2026-07-19", "kickoff_et": "15:00"},
}

def get_all_games():
    r = requests.get(f"{API_BASE}/get/games", timeout=10)
    r.raise_for_status()
    return r.json()

def find_target_games(games):
    results = []
    for game in games:
        stage = game.get("stage", "").lower()
        if any(k in stage for k in ["semi", "final"]):
            results.append(game)
    return results

def format_event_update(game):
    home = game.get("home_team", {}).get("name", "TBD")
    away = game.get("away_team", {}).get("name", "TBD")
    home_score = game.get("home_score", 0)
    away_score = game.get("away_score", 0)
    stage = game.get("stage", "Match")
    status = game.get("status", "scheduled")
    minute = game.get("minute", "")

    events = game.get("events", [])
    goals = [e for e in events if e.get("type") in ["goal", "own_goal", "penalty"]]
    cards = [e for e in events if e.get("type") in ["red_card", "yellow_red_card"]]

    lines = []
    lines.append(f"*{stage}*")
    lines.append(f"{home} {home_score} - {away_score} {away}")
    if minute:
        lines.append(f"_Minute: {minute}'_")
    lines.append(f"Status: {status}")

    if goals:
        lines.append("\n*Goals:*")
        for g in goals:
            player = g.get("player", "Unknown")
            team = g.get("team", "")
            min_ = g.get("minute", "?")
            gtype = "⚽" if g.get("type") == "goal" else ("🔴 OG" if g.get("type") == "own_goal" else "🎯 PEN")
            lines.append(f"{gtype} {player} ({team}) {min_}'")

    if cards:
        lines.append("\n*Red Cards:*")
        for c in cards:
            player = c.get("player", "Unknown")
            team = c.get("team", "")
            min_ = c.get("minute", "?")
            lines.append(f"🟥 {player} ({team}) {min_}'")

    return "\n".join(lines)

def run():
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}] skibtracker running...")
    try:
        data = get_all_games()
        games = data if isinstance(data, list) else data.get("games", data.get("data", []))
        targets = find_target_games(games)

        if not targets:
            print("No semi/final matches found yet in API — may not be populated until bracket resolves.")
            return None

        updates = []
        for game in targets:
            status = game.get("status", "")
            # Only report live or finished games with events
            if status in ["live", "finished", "halftime", "extra_time", "penalties"]:
                updates.append(format_event_update(game))

        if updates:
            return "\n\n---\n\n".join(updates)
        else:
            return "No live semi/final matches right now."

    except Exception as e:
        return f"skibtracker error: {e}"

if __name__ == "__main__":
    result = run()
    if result:
        print(result)
