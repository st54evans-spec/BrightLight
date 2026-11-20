"""Classic twins: match any game against every game since 1970.

Uses the grading points that exist in every era (QB, RB, WR, TE production and
what the defense had allowed), each as a percentile of its own season, plus the
setting. Every twin is listed on its own line with its season and players.

Usage: python src/classic_twins.py 2026_13_SF_NYG   or   --all-upcoming
"""
import os, sys
import numpy as np
import pandas as pd
from twins import dist

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(ROOT, "data", "processed")
OUTD = os.path.join(ROOT, "results", "classic_twins")
TZ = {"SEA": -3, "SF": -3, "LA": -3, "LAC": -3, "LV": -3, "DEN": -2, "ARI": -2,
      "CHI": -1, "DAL": -1, "GB": -1, "HOU": -1, "KC": -1, "MIN": -1, "NO": -1, "TEN": -1}

OFF = (["off_QB1_" + t for t in ["ypa", "adj_ypa", "comp_pct", "td_rate", "int_rate", "sack_rate"]]
       + ["off_RB1_ypc", "off_RB1_rush_td_rate", "off_RB1_carries_per_game"]
       + [f"off_WR{i}_{t}" for i in (1, 2) for t in ["ypr", "yds_per_game", "rec_per_game"]]
       + ["off_TE1_yds_per_game"]
       + ["def_pass_ypa_allowed", "def_int_forced", "def_sacks_forced", "def_pass_td_allowed", "def_rush_ypc_allowed"])
SET = [("home_f", 1), ("tz_trip", 3), ("temp_f", 50), ("dome_f", 1), ("week", 17)]


def load():
    c = pd.read_parquet(os.path.join(PROC, "classic_cells.parquet"))
    c["home_f"] = c.home.astype(float)
    c["dome_f"] = c.dome.fillna(False).astype(float)
    c["temp_f"] = c.temp.where(c.dome_f == 0, 70).fillna(60)
    c["tz_trip"] = c.tz_trip.fillna(0)
    return c


def target_rows(c, gid):
    t = c[c.game_key == gid]
    if len(t) == 2:
        return t
    g = pd.read_csv(os.path.join(ROOT, "data/raw/games.csv")).set_index("game_id").loc[gid]
    rows = []
    for team, opp, home in [(g.home_team, g.away_team, True), (g.away_team, g.home_team, False)]:
        last = c[(c.team == team) & (c.date < pd.Timestamp(g.gameday))].sort_values("date").tail(1).iloc[0].copy()
        dl = c[(c.opp == opp) & (c.date < pd.Timestamp(g.gameday))].sort_values("date").tail(1).iloc[0]
        for col in [x for x in c.columns if x.startswith("def_")]:
            last[col] = dl[col]
        last["game_key"], last["opp"], last["home_f"] = gid, opp, float(home)
        last["date"], last["week"], last["pts_for"], last["pts_against"] = pd.Timestamp(g.gameday), g.week, np.nan, np.nan
        last["tz_trip"] = 0 if home else TZ.get(opp, 0) - TZ.get(team, 0)
        last["dome_f"] = float(g.roof in ("dome", "closed"))
        last["temp_f"] = 70 if last["dome_f"] else (g.temp if pd.notna(g.temp) else 50)
        rows.append(last)
    return pd.DataFrame(rows)


def report(gid, c):
    t = target_rows(c, gid)
    home = t[t.home_f == 1].iloc[0]; away = t[t.home_f == 0].iloc[0]
    pool = c[(c.date < home.date) & c.pts_for.notna()]
    ph = pool[pool.home_f == 1].drop_duplicates("game_key").set_index("game_key")
    pa = pool[pool.home_f == 0].drop_duplicates("game_key").set_index("game_key").reindex(ph.index)
    d1, n1 = dist(home, ph, OFF); d2, n2 = dist(away, pa, OFF)
    d3, _ = dist(home, ph, SET, setting=True)
    top = ph.assign(_d=(d1 + d2 + d3) / 3).dropna(subset=["_d"]).nsmallest(25, "_d")
    f = lambda v: "" if pd.isna(v) else f"{v:.0f}"
    L = [f"# Classic twins since 1970: {away.team} at {home.team} ({gid})", "",
         "Matched on QB, RB, WR and TE grading points (each a percentile of its own season), what each defense "
         "had allowed going in, and the setting (home/away, time zones travelled, temperature, dome, week). "
         "Only earlier games are searched. Every twin is listed on its own.", "",
         f"**This game going in:** {home.team} QB {home.off_QB1_name} (adj yds/att {f(home.off_QB1_adj_ypa)}, "
         f"INT rate {f(home.off_QB1_int_rate)}), RB {home.off_RB1_name}, WR {home.off_WR1_name}. "
         f"{away.team} QB {away.off_QB1_name} (adj yds/att {f(away.off_QB1_adj_ypa)}, INT rate {f(away.off_QB1_int_rate)}), "
         f"RB {away.off_RB1_name}, WR {away.off_WR1_name}.", "",
         "| Similarity | Season | Game | Home QB vs away QB | Home RB vs away RB | Setting | Score (home-away) |",
         "| --- | --- | --- | --- | --- | --- | --- |"]
    for k, r in top.iterrows():
        a = pa.loc[k]
        setting = f"{'dome' if r.dome_f else f'{r.temp_f:.0f}F'}, wk{r.week:.0f}, away crossed {abs(a.tz_trip):.0f} zones"
        L.append(f"| {100 * (1 - r._d):.0f} | {r.season:.0f} | {a.orig_team} at {r.orig_team} | {r.off_QB1_name} vs {a.off_QB1_name} | "
                 f"{r.off_RB1_name} vs {a.off_RB1_name} | {setting} | {r.pts_for:.0f}-{r.pts_against:.0f} |")
    era = top.season.floordiv(10).mul(10).value_counts().sort_index()
    L += ["", "Twins by decade: " + ", ".join(f"{int(k)}s: {v}" for k, v in era.items()),
          f"Home side won {(top.pts_for > top.pts_against).sum()} of {len(top)}.", ""]
    os.makedirs(OUTD, exist_ok=True)
    path = os.path.join(OUTD, f"{gid}.md")
    open(path, "w").write("\n".join(L))
    return path


if __name__ == "__main__":
    c = load()
    if sys.argv[1] == "--all-upcoming":
        g = pd.read_csv(os.path.join(ROOT, "data/raw/games.csv"))
        for gid in g[g.result.isna() & (g.season == g.season.max())].game_id:
            try:
                report(gid, c)
            except Exception as e:
                print("skip", gid, e)
        print("done")
    else:
        print(report(sys.argv[1], c))
