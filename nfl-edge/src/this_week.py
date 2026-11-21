"""This week's games, each with the past games that almost match it, one by one.

For every unplayed game in the given week, three separate searches, each listed
game by game in order of closeness (no hit rates, no averages of results):
  A. Player by player (1999-now): both offenses vs both defenses, every role's
     grades going in, plus the setting (home/away, travel, body clock, weather, week)
  B. Madden teams (2001-2025): both teams' Madden units side by side (QB, RB, WR,
     TE, OL, DL, LB, DB)
  C. Deep history (1970-now): QB/RB/WR/TE production and what each defense had
     allowed, plus the setting
The top of the file ranks this week's games by how close their best player-by-
player matches are (closeness of the five nearest, 100 = identical).

Usage: python src/this_week.py 2026 11     -> results/THIS_WEEK.md
"""
import os, sys
import numpy as np
import pandas as pd
import twins
import classic_twins as ct
from madden_teams import OFFU, DEFU

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
UNITS = OFFU + DEFU


def ln(home_line):
    return "-" if pd.isna(home_line) else f"{home_line:+.1f}"


def player_twins(c, gid, n=10):
    tg = twins.upcoming_cell(c, gid)
    gd = tg.gd.iloc[0]
    pool = c[(c.gd < gd) & c.off_points.notna()]
    # This week's two teams' own games from this season are where their going-in grades come from, so they
    # would match themselves: leave those out and search the rest of history
    teams = set(tg.offense)
    pool = pool[~((pool.season == tg.season.iloc[0]) & (pool.offense.isin(teams) | pool.defense.isin(teams)))]
    home, away, top, pa = twins.whole_game(tg, pool, n)
    rows = []
    for gid2, r in top.iterrows():
        a = pa.loc[gid2]
        rows.append({"close": 100 * (1 - r._d), "date": r.gameday, "game": f"{r._a} at {r.offense}",
                     "qbs": f"{a.off_QB1_player_display_name} at {r.off_QB1_player_display_name}",
                     "setting": f"{r.roof}{'' if pd.isna(r.temp) else f', {r.temp:.0f}F'}, wk {r.week}, "
                                f"away body clock {a.off_body_clock_hour:.0f}:00",
                     "score": f"{r._ap:.0f}-{r.off_points:.0f}", "line": ln(-r.line),
                     "vs": "-" if pd.isna(r.result_vs_line) else f"{r.result_vs_line:+.1f}"})
    return home, away, rows


def madden_twins(mg, gid, n=10):
    r = mg[mg.game_id == gid]
    if r.empty or r[[f"home_unit_{u}" for u in UNITS]].isna().all(axis=1).iloc[0]:
        return None, []
    r = r.iloc[0]
    cols = [f"{s}_unit_{u}" for s in ("home", "away") for u in UNITS]
    pool = mg[mg.home_score.notna() & (mg.season <= 2025)].dropna(subset=cols)
    d = (pool[cols] - r[cols].astype(float).values).abs().mean(axis=1)
    top = pool.assign(_d=d).nsmallest(n, "_d")
    rows = [{"close": max(0, 100 - 10 * x._d), "date": x.gameday, "game": f"{x.away_team} at {x.home_team}",
             "qbs": f"{x.away_QB_name} at {x.home_QB_name}",
             "units": " ".join(f"{u} {x[f'home_unit_{u}']:.0f}/{x[f'away_unit_{u}']:.0f}" for u in UNITS),
             "score": f"{x.away_score:.0f}-{x.home_score:.0f}", "line": ln(-x.spread_line),
             "vs": "-" if pd.isna(x.home_vs_line) else f"{x.home_vs_line:+.1f}"} for _, x in top.iterrows()]
    return r, rows


def classic(cc, gid, n=10):
    t = ct.target_rows(cc, gid)
    home = t[t.home_f == 1].iloc[0]; away = t[t.home_f == 0].iloc[0]
    pool = cc[(cc.date < home.date) & cc.pts_for.notna()]
    yr = home.date.year if home.date.month > 2 else home.date.year - 1
    pool = pool[~((pool.season == yr) & (pool.team.isin([home.team, away.team]) | pool.opp.isin([home.team, away.team])))]
    ph = pool[pool.home_f == 1].drop_duplicates("game_key").set_index("game_key")
    pa = pool[pool.home_f == 0].drop_duplicates("game_key").set_index("game_key").reindex(ph.index)
    d1, _ = twins.dist(home, ph, ct.OFF); d2, _ = twins.dist(away, pa, ct.OFF)
    d3, _ = twins.dist(home, ph, ct.SET, setting=True)
    top = ph.assign(_d=(d1 + d2 + d3) / 3).dropna(subset=["_d"]).nsmallest(n, "_d")
    rows = []
    for k, r in top.iterrows():
        a = pa.loc[k]
        rows.append({"close": 100 * (1 - r._d), "season": int(r.season), "game": f"{a.orig_team} at {r.orig_team}",
                     "qbs": f"{a.off_QB1_name} at {r.off_QB1_name}", "rbs": f"{a.off_RB1_name} / {r.off_RB1_name}",
                     "setting": f"{'dome' if r.dome_f else f'{r.temp_f:.0f}F'}, wk {r.week:.0f}, away crossed {abs(a.tz_trip):.0f} zones",
                     "score": f"{r.pts_against:.0f}-{r.pts_for:.0f}"})
    return rows


def main(season, week):
    g = pd.read_csv(os.path.join(ROOT, "data", "raw", "games.csv"))
    wk = g[(g.season == season) & (g.week == week) & g.home_score.isna()].sort_values(["gameday", "gametime"])
    if len(sys.argv) > 3:                       # optional: only games on or after this date
        wk = wk[wk.gameday >= sys.argv[3]]
    c = twins.load()
    cc = ct.load()
    mg = pd.read_csv(os.path.join(RES, "madden_team_games.csv"))
    out = []
    for _, gm in wk.iterrows():
        gid = gm.game_id
        try:
            home, away, pt = player_twins(c, gid)
        except Exception as e:
            print("player twins skip", gid, e); home, away, pt = None, None, []
        try:
            mr, mt = madden_twins(mg, gid)
        except Exception as e:
            print("madden skip", gid, e); mr, mt = None, []
        try:
            cl = classic(cc, gid)
        except Exception as e:
            print("classic skip", gid, e); cl = []
        out.append((gm, home, away, pt, mr, mt, cl))
    top5 = lambda rows: np.mean([r["close"] for r in rows[:5]]) if rows else np.nan
    out.sort(key=lambda x: -np.nan_to_num(top5(x[3]), nan=-1))

    L = [f"# Week {week}, {season}: the past games that almost match each game", "",
         "Each past game is listed on its own, closest first. Closeness 100 = identical going in. "
         "Score is shown away-home, the home line is in betting terms (-3.0 = home favored by 3), and "
         "\"home vs line\" is how many points the home side beat (+) or missed (-) the spread by. "
         "This season's own games for the two teams are left out of every search (their going-in grades come from those games).", "",
         "## This week's games, tightest past matches first", "",
         "| Game | Date | Home line | Player-by-player: closest 5 | Madden teams: closest 5 | Since 1970: closest 5 | Closest single past game |",
         "| --- | --- | --- | --- | --- | --- | --- |"]
    for gm, home, away, pt, mr, mt, cl in out:
        best = pt[0] if pt else None
        L.append(f"| {gm.away_team} at {gm.home_team} | {gm.gameday} | {ln(-gm.spread_line)} | {top5(pt):.0f} | "
                 f"{top5(mt):.0f} | {top5(cl):.0f} | "
                 + (f"{best['date']} {best['game']} ({best['qbs']}), {best['score']}" if best else "-") + " |")
    for gm, home, away, pt, mr, mt, cl in out:
        L += ["", "---", "", f"## {gm.away_team} at {gm.home_team}, {gm.gameday} {gm.gametime} ET, week {week}", "",
              f"Home line {ln(-gm.spread_line)}, total {gm.total_line if pd.notna(gm.total_line) else '-'}. "
              f"QBs going in: {away.off_QB1_player_display_name if away is not None else gm.away_qb_name} at "
              f"{home.off_QB1_player_display_name if home is not None else gm.home_qb_name}. Roof: {gm.roof}.", ""]
        if mr is not None:
            L += ["Madden 27 units (home/away): " + " ".join(f"{u} {mr[f'home_unit_{u}']:.0f}/{mr[f'away_unit_{u}']:.0f}" for u in UNITS), ""]
        L += ["### A. Player by player (every role's grades + setting)", "",
              "| # | Closeness | Date | Past game | QBs | Setting | Score | Home line | Home vs line |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for i, r in enumerate(pt, 1):
            L.append(f"| {i} | {r['close']:.0f} | {r['date']} | {r['game']} | {r['qbs']} | {r['setting']} | {r['score']} | {r['line']} | {r['vs']} |")
        L += ["", "### B. Madden teams (units side by side, home/away)", "",
              "| # | Closeness | Date | Past game | QBs | Units home/away | Score | Home line | Home vs line |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for i, r in enumerate(mt, 1):
            L.append(f"| {i} | {r['close']:.0f} | {r['date']} | {r['game']} | {r['qbs']} | {r['units']} | {r['score']} | {r['line']} | {r['vs']} |")
        L += ["", "### C. Since 1970 (QB/RB/WR/TE production, defense allowed, setting)", "",
              "| # | Closeness | Season | Past game | QBs | RBs | Setting | Score |",
              "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        for i, r in enumerate(cl, 1):
            L.append(f"| {i} | {r['close']:.0f} | {r['season']} | {r['game']} | {r['qbs']} | {r['rbs']} | {r['setting']} | {r['score']} |")
    open(os.path.join(RES, "THIS_WEEK.md"), "w").write("\n".join(L).replace(" nan ", " ? ").replace(" at nan", " at ?").replace("nan at ", "? at "))
    print("\n".join(L[:20]))


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
