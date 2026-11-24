"""List past trips that match an upcoming game, one game at a time.

Matching works in layers, each one narrower than the last, in this order:
  1. same home region travelling the same way across the same number of zones
  2. + same body-clock kickoff (within 1 hour)
  3. + same side of the clock change
  4. + similar rest (within 1 day)
  5. + same travelling team
  6. + exact route (same team, same opponent)
Every game in every layer is listed with its own details. Nothing is averaged.

Usage: python src/find_matches.py SF NYG 2026-12-06
"""
import os, sys
import pandas as pd
from trip_ledger import tz, REGION, fall_back_sunday, ROOT

FRANCHISE = {"SD": "LAC", "OAK": "LV", "STL": "LA"}
COLS = ["date", "team", "opp", "to", "body_clock", "kickoff_local", "days_after_clock_change",
        "rest_days", "opp_rest_days", "prev_game", "road_games_in_row_before", "temp_F", "wind_mph",
        "my_qb", "opp_qb", "my_pass_off_pct", "opp_pass_def_bad_pct", "my_pass_def_bad_pct",
        "opp_pass_off_pct", "line", "score", "vs_line", "result", "upset"]


def clock_minutes(s):
    h, m = map(int, s.split(":"))
    return h * 60 + m


def query(team, opp, date):
    g = pd.read_csv(os.path.join(ROOT, "data/raw/games.csv"))
    x = g[(g.away_team == team) & (g.home_team == opp) & (g.gameday == date)].iloc[0]
    d = pd.Timestamp(date).date()
    origin, dest = tz(team, d, x.season), tz(opp, d, x.season)
    h, m = map(int, x.gametime.split(":"))
    return {
        "team": team, "opp": opp, "date": date, "stadium": x.stadium,
        "zones": dest - origin, "from": REGION[team],
        "body_clock": f"{(h + origin) % 24:02d}:{m:02d}",
        "after_change": d >= fall_back_sunday(x.season),
        "rest": x.away_rest, "line": -x.spread_line,
    }


def layers(t, q):
    t = t.dropna(subset=["body_clock"]).copy()
    t["body_min"] = t.body_clock.map(clock_minutes)
    qb = clock_minutes(q["body_clock"])
    steps = [
        (f"{q['from']} team crossing {q['zones']:+d} zones", (t["from"] == q["from"]) & (t.zones == q["zones"])),
        (f"+ body-clock kickoff near {q['body_clock']}", (t.body_min - qb).abs() <= 60),
        ("+ " + ("after" if q["after_change"] else "before") + " the clock change",
         (t.days_after_clock_change >= 0) == q["after_change"]),
        (f"+ rest within 1 day of {q['rest']}", (t.rest_days - q["rest"]).abs() <= 1),
        (f"+ same franchise ({q['team']})", t.team.map(lambda c: FRANCHISE.get(c, c)) == FRANCHISE.get(q["team"], q["team"])),
        (f"+ exact route ({q['team']} at {q['opp']})", t.opp == q["opp"]),
    ]
    mask = pd.Series(True, index=t.index)
    out = []
    for name, cond in steps:
        mask &= cond
        out.append((name, t[mask].sort_values("date", ascending=False)))
    return out


def fmt(r):
    up = " UPSET" if r.upset else ""
    w = "" if pd.isna(r.temp_F) else f", {int(r.temp_F)}F wind {int(r.wind_mph) if pd.notna(r.wind_mph) else '?'}"
    return (f"| {r.date} | {r.team} at {r.opp} | {r.body_clock} | {r.days_after_clock_change:+d} | "
            f"{int(r.rest_days)} v {int(r.opp_rest_days)} | {r.prev_game or ''} | {r.my_qb} v {r.opp_qb} | "
            f"{r.my_pass_off_pct:.2f} v {r.opp_pass_def_bad_pct:.2f} | {r.line:+.1f} | {r.score} | "
            f"{r.vs_line:+.1f}{up}{w} |")


def report(team, opp, date):
    q = query(team, opp, date)
    t = pd.read_csv(os.path.join(ROOT, "results/trip_ledger.csv"))
    lines = [f"# {team} at {opp}, {date}", "",
             f"{q['stadium']}. {team} crosses {q['zones']:+d} time zones; kickoff feels like "
             f"{q['body_clock']} on their body clock; {'after' if q['after_change'] else 'before'} the clock change; "
             f"{q['rest']} days rest; line " + ("not set yet" if pd.isna(q['line']) else f"{q['line']:+.1f} for {team}") + ".", "",
             "Each layer adds one condition to the one above it. Every matching game is listed.", "",
             "Columns: body clock = kickoff time back home; clock = days after the fall-back Sunday; "
             "rest = traveller v home; pass = traveller's pass offense rank v home pass defense weakness "
             "(1.00 = best offense / worst defense); line and result from the traveller's side; "
             "vs line = points better (+) or worse (-) than the spread.", ""]
    for name, d in layers(t, q):
        wl = f"{(d.result == 'W').sum()}-{(d.result == 'L').sum()}"
        lines += [f"## {name}: {len(d)} games ({wl})", ""]
        if len(d) > 40:
            lines += [f"Showing the 40 most recent of {len(d)}. Full list in the ledger.", ""]
        lines += ["| Date | Game | Body clock | Clock | Rest | Prev | QBs | Pass | Line | Score | vs line |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        lines += [fmt(r) for r in d.head(40).itertuples()]
        lines.append("")
    path = os.path.join(ROOT, "results", "matches", f"{date}_{team}_at_{opp}.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write("\n".join(lines))
    return path


if __name__ == "__main__":
    print(report(*sys.argv[1:4]))
