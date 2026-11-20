"""Classic grading points, 1970 to now, on one scale.

Before 1999 the only player data we can reach is per-game passing, rushing and
receiving logs (QB, RB, WR, TE) scraped from Pro Football Reference and
published on GitHub (jawkneemai/PFRWebScrape). From 1999 the same numbers come
from nflverse. Every grade is a percentile within its own season, so a 1975 QB
and a 2025 QB are compared against their own league, not raw numbers.

Defenses before 1999 are graded by what opposing QBs and runners did against
them (yards per attempt allowed, interceptions forced, sacks, yards per carry).

Output: data/processed/classic_cells.parquet, one row per offense per game since 1970.
"""
import os
import numpy as np
import pandas as pd
from grades import rolling

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
PROC = os.path.join(ROOT, "data", "processed")
H = os.path.join(RAW, "history", "pfr_logs")

BASE = ["n", "name", "pos", "age", "date", "lg", "team", "at", "opp", "result", "game_no", "week", "day"]


def franchise(code, year):
    m = {"GNB": "GB", "KAN": "KC", "NOR": "NO", "NWE": "NE", "BOS": "NE", "SDG": "LAC", "SFO": "SF",
         "TAM": "TB", "RAI": "LV", "OAK": "LV", "RAM": "LA", "LAR": "LA", "PHO": "ARI", "TEN": "TEN"}
    if code == "STL":
        return "ARI" if year < 1990 else "LA"
    if code == "HOU":
        return "TEN" if year < 2000 else "HOU"
    if code == "BAL":
        return "IND" if year < 1990 else "BAL"
    return m.get(code, code)


def region(code, year):
    """Home time zone of the team in that year, hours from Eastern."""
    west = {"RAI", "OAK", "RAM", "LAR", "SDG", "SFO", "SEA", "LAC", "SF", "LA", "LV", "SD"}
    central = {"CHI", "DAL", "GNB", "KAN", "MIN", "NOR", "TEN", "GB", "KC", "NO"}
    if code in west:
        return -3
    if code in ("DEN",):
        return -2
    if code in ("PHO", "ARI"):
        return -2
    if code == "STL" or code == "HOU":
        return -1
    return -1 if code in central else 0


def load_old():
    p = pd.read_csv(f"{H}/pass_game_logs.csv", header=None,
                    names=BASE + ["cmp", "att", "cmp_pct", "pass_yds", "pass_td", "int", "rating", "sk", "sk_yds", "ypa", "aypa"])
    r = pd.read_csv(f"{H}/rush_game_logs.csv", header=None, names=BASE + ["car", "rush_yds", "ypc", "rush_td"])
    c = pd.read_csv(f"{H}/rec_game_logs.csv", header=None,
                    names=BASE + ["tgt", "rec", "rec_yds", "ypr", "rec_td", "ctch", "ypt"])
    keys = ["name", "date", "team", "opp", "at", "result", "week", "pos", "age"]
    d = p[keys + ["cmp", "att", "pass_yds", "pass_td", "int", "sk"]].merge(
        r[keys + ["car", "rush_yds", "rush_td"]], on=keys, how="outer").merge(
        c[keys + ["tgt", "rec", "rec_yds", "rec_td"]], on=keys, how="outer")
    d["date"] = pd.to_datetime(d.date)
    d["season"] = np.where(d.date.dt.month <= 2, d.date.dt.year - 1, d.date.dt.year)
    d = d[d.season < 1999].copy()
    d["home"] = d["at"] != "@"
    d["neutral"] = d["at"] == "N"
    d["orig_team"], d["orig_opp"] = d.team, d.opp
    d["team"] = [franchise(t, y) for t, y in zip(d.team, d.season)]
    d["opp"] = [franchise(t, y) for t, y in zip(d.opp, d.season)]
    sc = d.result.str.extract(r"([WLT]) (\d+)-(\d+)")
    d["pts_for"], d["pts_against"] = sc[1].astype(float), sc[2].astype(float)
    d["pos"] = d.pos.str.upper().replace({"HB": "RB", "FB": "RB"})
    d["player_id"] = "old_" + d.name.str.replace(" ", "_") + "_" + d.groupby("name").date.transform("min").dt.year.astype(str)
    d["game_key"] = d.date.dt.strftime("%Y-%m-%d") + "_" + np.where(d.home, d.opp + "_at_" + d.team, d.team + "_at_" + d.opp)
    return d


def load_new():
    pg = pd.read_parquet(os.path.join(PROC, "player_games.parquet"),
                         columns=["game_id", "player_id", "player_display_name", "position", "team", "opponent_team",
                                  "season", "season_type", "gameday", "age", "completions", "attempts", "passing_yards",
                                  "passing_tds", "passing_interceptions", "sacks_suffered", "carries", "rushing_yards",
                                  "rushing_tds", "targets", "receptions", "receiving_yards", "receiving_tds"])
    pg = pg[pg.position.isin(["QB", "RB", "FB", "WR", "TE"])]
    g = pd.read_csv(os.path.join(RAW, "games.csv")).set_index("game_id")
    d = pd.DataFrame({
        "name": pg.player_display_name, "player_id": pg.player_id, "pos": pg.position.replace({"FB": "RB"}),
        "age": pg.age, "date": pg.gameday, "season": pg.season,
        "team": pg.team, "opp": pg.opponent_team, "orig_team": pg.team, "orig_opp": pg.opponent_team,
        "home": pg.team == pg.game_id.map(g.home_team), "neutral": pg.game_id.map(g.location) == "Neutral",
        "cmp": pg.completions, "att": pg.attempts, "pass_yds": pg.passing_yards, "pass_td": pg.passing_tds,
        "int": pg.passing_interceptions, "sk": pg.sacks_suffered, "car": pg.carries, "rush_yds": pg.rushing_yards,
        "rush_td": pg.rushing_tds, "tgt": pg.targets, "rec": pg.receptions, "rec_yds": pg.receiving_yards,
        "rec_td": pg.receiving_tds, "week": pg.game_id.map(g.week), "game_key": pg.game_id,
    })
    hs = pg.game_id.map(g.home_score); as_ = pg.game_id.map(g.away_score)
    d["pts_for"] = np.where(d.home, hs, as_); d["pts_against"] = np.where(d.home, as_, hs)
    fix = {"STL": "LA", "OAK": "LV", "SD": "LAC"}
    d["team"] = d.team.replace(fix); d["opp"] = d.opp.replace(fix)
    return d


def z(x):
    return x.fillna(0)


CLASSIC = {
    "QB": [("ypa", lambda d: z(d.pass_yds), lambda d: z(d.att), True),
           ("adj_ypa", lambda d: z(d.pass_yds) + 20 * z(d.pass_td) - 45 * z(d["int"]), lambda d: z(d.att), True),
           ("comp_pct", lambda d: z(d.cmp), lambda d: z(d.att), True),
           ("td_rate", lambda d: z(d.pass_td), lambda d: z(d.att), True),
           ("int_rate", lambda d: z(d["int"]), lambda d: z(d.att), False),
           ("sack_rate", lambda d: z(d.sk), lambda d: (z(d.att) + z(d.sk)).where(d.sk.notna(), 0), False),
           ("rush_ypc", lambda d: z(d.rush_yds), lambda d: z(d.car), True)],
    "RB": [("ypc", lambda d: z(d.rush_yds), lambda d: z(d.car), True),
           ("rush_td_rate", lambda d: z(d.rush_td), lambda d: z(d.car), True),
           ("carries_per_game", lambda d: z(d.car), lambda d: pd.Series(1.0, index=d.index), True),
           ("rec_yds_per_game", lambda d: z(d.rec_yds), lambda d: pd.Series(1.0, index=d.index), True)],
    "WR": [("ypr", lambda d: z(d.rec_yds), lambda d: z(d.rec), True),
           ("yds_per_game", lambda d: z(d.rec_yds), lambda d: pd.Series(1.0, index=d.index), True),
           ("rec_per_game", lambda d: z(d.rec), lambda d: pd.Series(1.0, index=d.index), True),
           ("rec_td_rate", lambda d: z(d.rec_td), lambda d: z(d.rec), True),
           ("catch_rate", lambda d: z(d.rec), lambda d: z(d.tgt), True)],
}
CLASSIC["TE"] = CLASSIC["WR"]


def grade(d):
    d = d.sort_values(["player_id", "date"]).reset_index(drop=True)
    out = []
    for pos, T in CLASSIC.items():
        sub = d[d.pos == pos]
        cols = {}
        for name, fn, fd, hib in T:
            num, den = fn(sub), fd(sub)
            k = max(den[den > 0].median() * 3, 1e-6)
            sr = num.groupby(sub.season).sum() / den.groupby(sub.season).sum().replace(0, np.nan)
            prev = sub.season.map(sr.shift(1).fillna(sr))
            pn, pdn = rolling(sub, num, den, k)
            rate = pd.Series((pn + prev.values * k) / (pdn + k), index=sub.index).where(pdn > 0)
            pct = rate.groupby(sub.season).rank(pct=True)
            if not hib:
                pct = 1 - pct + 1 / rate.groupby(sub.season).transform("count")
            cols[f"c_{name}"] = (pct * 100).round(1)
        out.append(pd.DataFrame(cols, index=sub.index))
    return pd.concat([d, pd.concat(out)], axis=1)


def defense_profile(d):
    """Per team-game, what the defense had allowed going in (earlier games only), as season percentiles."""
    qb = d[d.pos == "QB"].groupby(["game_key", "opp", "date", "season"]).agg(
        att=("att", "sum"), yds=("pass_yds", "sum"), ints=("int", "sum"), sk=("sk", "sum"), td=("pass_td", "sum")).reset_index()
    ru = d[d.pos.isin(["RB", "QB", "WR"])].groupby(["game_key", "opp"]).agg(car=("car", "sum"), ryds=("rush_yds", "sum")).reset_index()
    t = qb.merge(ru, on=["game_key", "opp"], how="left").rename(columns={"opp": "team"})
    t = t.sort_values(["team", "date"]).reset_index(drop=True)
    t["player_id"] = t.team
    res = {}
    for name, num, den, hib in [("pass_ypa_allowed", t.yds, t.att, False), ("int_forced", t.ints, t.att, True),
                                ("sacks_forced", t.sk.fillna(0), (t.att + t.sk.fillna(0)).where(t.sk.notna(), 0), True),
                                ("pass_td_allowed", t.td, t.att, False), ("rush_ypc_allowed", t.ryds, t.car, False)]:
        num, den = num.fillna(0), den.fillna(0)
        k = max(den[den > 0].median() * 3, 1e-6)
        sr = num.groupby(t.season).sum() / den.groupby(t.season).sum().replace(0, np.nan)
        prev = t.season.map(sr.shift(1).fillna(sr))
        pn, pdn = rolling(t, num, den, k)
        rate = pd.Series((pn + prev.values * k) / (pdn + k)).where(pdn > 0)
        pct = rate.groupby(t.season).rank(pct=True)
        if not hib:
            pct = 1 - pct + 1 / rate.groupby(t.season).transform("count")
        res[f"def_{name}"] = (pct * 100).round(1)
    return pd.concat([t[["game_key", "team"]], pd.DataFrame(res)], axis=1)


def build():
    d = pd.concat([load_old(), load_new()], ignore_index=True)
    d = d.dropna(subset=["date", "team"])
    d = grade(d)
    d.to_parquet(os.path.join(PROC, "classic_player_games.parquet"), index=False)
    # Offense roles per team-game: QB1 by attempts, RB1 by carries, WR1-2 and TE1 by receiving yards
    roles = []
    for role, pos, n, by in [("QB", ["QB"], 1, "att"), ("RB", ["RB"], 1, "car"), ("WR", ["WR"], 2, "rec_yds"), ("TE", ["TE"], 1, "rec_yds")]:
        s = d[d.pos.isin(pos)].assign(_u=lambda x: x[by].fillna(0)).sort_values(["game_key", "team", "_u"], ascending=[True, True, False])
        s["slot"] = s.groupby(["game_key", "team"]).cumcount() + 1
        s = s[s.slot <= n]
        gcols = [c for c in s.columns if c.startswith("c_") and s[c].notna().any()]
        w = s.pivot_table(index=["game_key", "team"], columns="slot", values=gcols + ["age"], aggfunc="first")
        w.columns = [f"off_{role}{int(sl)}_{c.replace('c_', '')}" for c, sl in w.columns]
        nm = s.pivot_table(index=["game_key", "team"], columns="slot", values="name", aggfunc="first")
        nm.columns = [f"off_{role}{int(sl)}_name" for sl in nm.columns]
        roles += [w, nm]
    cells = pd.concat(roles, axis=1).reset_index()
    info = d.groupby(["game_key", "team"]).agg(opp=("opp", "first"), date=("date", "first"), season=("season", "first"),
                                               week=("week", "first"), home=("home", "first"), neutral=("neutral", "first"),
                                               pts_for=("pts_for", "first"), pts_against=("pts_against", "first"),
                                               orig_team=("orig_team", "first"), orig_opp=("orig_opp", "first")).reset_index()
    cells = info.merge(cells, on=["game_key", "team"], how="left")
    dp = defense_profile(d).rename(columns={"team": "opp"})
    cells = cells.merge(dp, on=["game_key", "opp"], how="left")
    # Setting: weather, roof and lines from the 1966+ file (before 1999), nflverse after
    s = pd.read_csv(os.path.join(RAW, "history", "spreadspoke_scores.csv"))
    s["date"] = pd.to_datetime(s.schedule_date)
    s["dome"] = s.weather_detail.fillna("").str.contains("DOME", case=False)
    sm = s.groupby(["date", "score_home", "score_away"]).agg(temp=("weather_temperature", "first"), wind=("weather_wind_mph", "first"),
                                                           dome=("dome", "first"), fav=("team_favorite_id", "first"),
                                                           spread=("spread_favorite", "first"), home_name=("team_home", "first")).reset_index()
    hp = np.where(cells.home, cells.pts_for, cells.pts_against); ap = np.where(cells.home, cells.pts_against, cells.pts_for)
    cells = cells.assign(score_home=hp, score_away=ap).merge(sm, on=["date", "score_home", "score_away"], how="left")
    cells["tz_trip"] = [0 if h else region(o, y) - region(t, y) for t, o, h, y in zip(cells.orig_team, cells.orig_opp, cells.home, cells.season)]
    cells["margin"] = cells.pts_for - cells.pts_against
    cells.to_parquet(os.path.join(PROC, "classic_cells.parquet"), index=False)
    print("classic player-games", len(d), "cells", len(cells), "seasons", int(cells.season.min()), "-", int(cells.season.max()))


if __name__ == "__main__":
    build()
