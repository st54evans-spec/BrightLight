"""Trip ledger: every road game kept as its own record, nothing averaged.

Each row is one team travelling to one game, with the specifics of that
trip: where from, where to, how many time zones and which way, what time
the kickoff felt like on the traveller's body clock, which side of the
clock change, rest, the trip before, weather, field, both teams' passing
profile going in, the line, and what actually happened.
"""
import os, datetime as dt
import pandas as pd
import numpy as np
from dst_travel_test import load, pass_ratings, label, fall_back_sunday

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results")

EAST = ["ATL", "BAL", "BUF", "CAR", "CIN", "CLE", "DET", "IND", "JAX",
        "MIA", "NE", "NYG", "NYJ", "PHI", "PIT", "TB", "WAS"]
CENTRAL = ["CHI", "DAL", "GB", "HOU", "KC", "MIN", "NO", "TEN", "STL"]
WEST = ["LA", "LAC", "LV", "OAK", "SD", "SEA", "SF"]
REGION = {**{t: "East" for t in EAST}, **{t: "Central" for t in CENTRAL},
          **{t: "West" for t in WEST}, "DEN": "Mountain", "ARI": "Arizona"}
# Neutral-site stadiums by nflverse stadium_id prefix, hours from US Eastern (US daylight time)
INTL = {"LON": 5, "MEX": -1, "GER": 6, "FRA": 6, "SAO": 1, "TOR": 0, "DUB": 5, "MAD": 6}


def tz(team, date, season):
    """Hours from Eastern for a team's home city on that date."""
    r = REGION[team]
    if r == "Arizona":  # no daylight saving: same as Pacific until fall back, Mountain after
        return -3 if date < fall_back_sunday(season) else -2
    return {"East": 0, "Central": -1, "Mountain": -2, "West": -3}[r]


def build():
    g = label(load(), pass_ratings())
    g = g.sort_values("gameday")
    # Each team's previous game, to know the trip before this one
    sched = pd.concat([
        pd.DataFrame({"team": g.home_team, "game_id": g.game_id, "gameday": g.gameday,
                      "season": g.season, "was_home": g.location == "Home"}),
        pd.DataFrame({"team": g.away_team, "game_id": g.game_id, "gameday": g.gameday,
                      "season": g.season, "was_home": False}),
    ]).sort_values(["team", "gameday"])
    sched["prev_home"] = sched.groupby(["team", "season"]).was_home.shift(1)
    sched["road_streak"] = sched.groupby(["team", "season"]).was_home.transform(
        lambda s: s.eq(False).groupby(s.ne(False).cumsum()).cumsum().shift(1).fillna(0))
    prev = sched.set_index(["game_id", "team"])[["prev_home", "road_streak"]]

    rows = []
    for _, x in g.iterrows():
        neutral = x.location == "Neutral"
        sid = str(x.stadium_id)[:3]
        for me, op in [("away", "home"), ("home", "away")]:
            if me == "home" and not neutral:
                continue  # home teams didn't travel
            team, opp = x[f"{me}_team"], x[f"{op}_team"]
            if team not in REGION or opp not in REGION:
                continue
            origin = tz(team, x.gameday, x.season)
            dest = INTL.get(sid, tz(opp, x.gameday, x.season)) if neutral else tz(opp, x.gameday, x.season)
            sign = 1 if me == "home" else -1
            kick = x.gametime if isinstance(x.gametime, str) else None
            body = None
            if kick:
                h, m = map(int, kick.split(":"))
                body = f"{(h + origin) % 24:02d}:{m:02d}"
                local = f"{(h + dest) % 24:02d}:{m:02d}"
            p = prev.loc[(x.game_id, team)] if (x.game_id, team) in prev.index else None
            exp = sign * x.spread_line
            margin = sign * x.result
            rows.append({
                "date": x.gameday, "season": x.season, "week": x.week, "weekday": x.weekday,
                "team": team, "from": REGION[team], "opp": opp,
                "to": x.stadium, "intl": neutral and sid in INTL,
                "zones": dest - origin,
                "direction": "east" if dest > origin else "west" if dest < origin else "same zone",
                "kickoff_ET": kick, "kickoff_local": local if kick else None, "body_clock": body,
                "days_after_clock_change": x.days_after_fb,
                "rest_days": x[f"{me}_rest"], "opp_rest_days": x[f"{op}_rest"],
                "prev_game": None if p is None or pd.isna(p.prev_home) else ("home" if p.prev_home else "away"),
                "road_games_in_row_before": None if p is None else int(p.road_streak),
                "roof": x.roof, "surface": x.surface, "temp_F": x.temp, "wind_mph": x.wind,
                "div_game": bool(x.div_game),
                "my_pass_off_pct": round(x[f"{me}_off_pct"], 2), "my_pass_def_bad_pct": round(x[f"{me}_def_bad_pct"], 2),
                "opp_pass_off_pct": round(x[f"{op}_off_pct"], 2), "opp_pass_def_bad_pct": round(x[f"{op}_def_bad_pct"], 2),
                "my_qb": x[f"{me}_qb_name"], "opp_qb": x[f"{op}_qb_name"],
                "line": exp, "score": f"{int(x[f'{me}_score'])}-{int(x[f'{op}_score'])}",
                "margin": margin, "vs_line": margin - exp,
                "result": "W" if margin > 0 else "L" if margin < 0 else "T",
                "upset": exp < 0 and margin > 0,
                "moneyline": x[f"{me}_moneyline"],
            })
    t = pd.DataFrame(rows)
    os.makedirs(OUT, exist_ok=True)
    t.to_csv(os.path.join(OUT, "trip_ledger.csv"), index=False)
    return t


if __name__ == "__main__":
    t = build()
    print(len(t), "trips")
    print(t.tail(3).T)
