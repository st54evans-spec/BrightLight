"""Daylight saving travel test.

Question: when the clocks fall back, do travelling teams play differently
against expectations? And the user's specific spot: a weak pass defense
facing a strong passing offense that is a heavy favorite, with the weak
team travelling (or not) the week of the clock change.

Only information available before kickoff is used to label teams: pass
ratings are built from games earlier in the same season (blended with the
prior season early on).
"""
import os, math, datetime as dt
import pandas as pd
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results")

# Home time zone, as offset from Eastern in hours, using the code of the era.
TZ = {t: 0 for t in ["ATL", "BAL", "BUF", "CAR", "CIN", "CLE", "DET", "IND", "JAX",
                      "MIA", "NE", "NYG", "NYJ", "PHI", "PIT", "TB", "WAS"]}
TZ.update({t: -1 for t in ["CHI", "DAL", "GB", "HOU", "KC", "MIN", "NO", "TEN", "STL"]})
TZ.update({"DEN": -2, "ARI": -2})  # Arizona keeps standard time: -3 in Sep/Oct, -2 after fall back
TZ.update({t: -3 for t in ["LA", "LAC", "LV", "OAK", "SD", "SEA", "SF"]})
PBP_CODE = {"STL": "LA", "OAK": "LV", "SD": "LAC"}

HEAVY_FAV = 6.5  # points


def fall_back_sunday(year):
    """US clocks fall back: last Sunday of October before 2007, first Sunday of November since."""
    if year >= 2007:
        d = dt.date(year, 11, 1)
        return d + dt.timedelta(days=(6 - d.weekday()) % 7)
    d = dt.date(year, 10, 31)
    return d - dt.timedelta(days=(d.weekday() - 6) % 7)


def load():
    g = pd.read_csv(os.path.join(ROOT, "data/raw/games.csv"))
    g = g[(g.game_type == "REG") & g.result.notna()].copy()
    g["gameday"] = pd.to_datetime(g.gameday).dt.date
    fb = {y: fall_back_sunday(y) for y in g.season.unique()}
    g["days_after_fb"] = [(d - fb[s]).days for d, s in zip(g.gameday, g.season)]
    g["dst_week"] = g.days_after_fb.between(0, 6)
    return g


def pass_ratings():
    t = pd.read_csv(os.path.join(ROOT, "data/processed/team_game_pass.csv"))
    t = t.sort_values(["season", "week"])
    rows = []
    for side, team_col in [("off", "posteam"), ("def", "defteam")]:
        x = t.groupby(["season", "week", "game_id", team_col])[["pass_epa", "pass_plays"]].sum().reset_index()
        x = x.rename(columns={team_col: "team"}).sort_values(["team", "season", "week"])
        grp = x.groupby(["team", "season"])
        x["cum_epa"] = grp.pass_epa.cumsum() - x.pass_epa
        x["cum_plays"] = grp.pass_plays.cumsum() - x.pass_plays
        season_rate = x.groupby(["team", "season"]).apply(
            lambda d: d.pass_epa.sum() / d.pass_plays.sum(), include_groups=False).rename("full")
        prev = season_rate.reset_index()
        prev["season"] += 1
        x = x.merge(prev, on=["team", "season"], how="left")
        prior = x.full.fillna(0) * 0.5          # regress last season halfway to average
        k = 150                                  # prior worth ~150 dropbacks (about 4 games)
        x[f"{side}_pass"] = (x.cum_epa + prior * k) / (x.cum_plays + k)
        rows.append(x[["game_id", "team", f"{side}_pass"]])
    r = rows[0].merge(rows[1], on=["game_id", "team"], how="outer")
    return r


def label(g, r):
    for side in ["home", "away"]:
        g[f"{side}_pbp"] = g[f"{side}_team"].map(lambda c: PBP_CODE.get(c, c))
        g = g.merge(r.rename(columns={"team": f"{side}_pbp", "off_pass": f"{side}_off_pass",
                                      "def_pass": f"{side}_def_pass"}),
                    on=["game_id", f"{side}_pbp"], how="left")
    # Weekly percentile ranks (higher = better offense; higher def EPA allowed = worse defense)
    for side in ["home", "away"]:
        g[f"{side}_off_pct"] = np.nan
        g[f"{side}_def_bad_pct"] = np.nan
    for (s, w), idx in g.groupby(["season", "week"]).groups.items():
        sub = g.loc[idx]
        off = pd.concat([sub.home_off_pass, sub.away_off_pass])
        de = pd.concat([sub.home_def_pass, sub.away_def_pass])
        for side in ["home", "away"]:
            g.loc[idx, f"{side}_off_pct"] = sub[f"{side}_off_pass"].apply(lambda v: (off < v).mean())
            g.loc[idx, f"{side}_def_bad_pct"] = sub[f"{side}_def_pass"].apply(lambda v: (de < v).mean())
    return g


def team_rows(g):
    """One row per team per game, from that team's point of view."""
    out = []
    for me, op in [("home", "away"), ("away", "home")]:
        sign = 1 if me == "home" else -1
        d = pd.DataFrame({
            "game_id": g.game_id, "season": g.season, "week": g.week, "gameday": g.gameday,
            "team": g[f"{me}_team"], "opp": g[f"{op}_team"],
            "is_home": (me == "home") & (g.location == "Home"),
            "neutral": g.location == "Neutral",
            "margin": sign * g.result,
            "exp_margin": sign * g.spread_line,
            "ml": g[f"{me}_moneyline"],
            "dst_week": g.dst_week, "days_after_fb": g.days_after_fb,
            "my_def_bad_pct": g[f"{me}_def_bad_pct"], "opp_off_pct": g[f"{op}_off_pct"],
            "my_off_pct": g[f"{me}_off_pct"], "opp_def_bad_pct": g[f"{op}_def_bad_pct"],
            "tz_shift": [TZ[o] - TZ[m] for m, o in zip(g[f"{me}_team"], g[f"{op}_team"])],
        })
        d.loc[d.is_home | d.neutral, "tz_shift"] = 0
        out.append(d)
    t = pd.concat(out, ignore_index=True)
    t["travelling"] = ~t.is_home & ~t.neutral
    t["vs_line"] = t.margin - t.exp_margin          # positive = beat the spread
    t["covered"] = np.where(t.vs_line == 0, np.nan, (t.vs_line > 0).astype(float))
    t["won"] = (t.margin > 0).astype(float)
    t["underdog"] = t.exp_margin < 0
    t["ml_profit"] = np.where(t.ml.isna(), np.nan,
                              np.where(t.won == 1, np.where(t.ml > 0, t.ml / 100, 100 / t.ml.abs()), -1.0))
    return t


def summarize(d, name):
    n = len(d)
    if n == 0:
        return {"spot": name, "games": 0}
    cov = d.covered.dropna()
    p = cov.mean() if len(cov) else np.nan
    se = math.sqrt(0.25 / len(cov)) if len(cov) else np.nan
    z = (p - 0.5) / se if len(cov) else np.nan
    ml = d.ml_profit.dropna()
    return {
        "spot": name, "games": n,
        "win_%": round(100 * d.won.mean(), 1),
        "expected_win_%": round(100 * (d.exp_margin > 0).mean() + 50 * (d.exp_margin == 0).mean(), 1),
        "cover_%": round(100 * p, 1),
        "avg_pts_vs_line": round(d.vs_line.mean(), 2),
        "z_score": round(z, 2),
        "ml_games": len(ml),
        "ml_roi_%": round(100 * ml.mean(), 1) if len(ml) else np.nan,
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    g = label(load(), pass_ratings())
    t = team_rows(g)
    t.to_csv(os.path.join(OUT, "team_games_labeled.csv"), index=False)
    trav = t[t.travelling]
    res = []
    # 1. Travelling teams: clock-change week vs the rest of the season
    res.append(summarize(trav[trav.dst_week], "A1 Travelling, clock-change week"))
    res.append(summarize(trav[~trav.dst_week], "A2 Travelling, all other weeks"))
    res.append(summarize(trav[trav.days_after_fb.between(-7, -1)], "A3 Travelling, week before the change"))
    # 2. By direction of travel in clock-change week
    for lab, cond in [("west to east (2+ zones)", trav.tz_shift >= 2),
                      ("east to west (2+ zones)", trav.tz_shift <= -2),
                      ("same or 1 zone", trav.tz_shift.abs() <= 1)]:
        res.append(summarize(trav[trav.dst_week & cond], f"B Travelling {lab}, clock-change week"))
        res.append(summarize(trav[~trav.dst_week & cond], f"B Travelling {lab}, other weeks"))
    # 3. The user's spot: weak pass D underdog vs strong pass O heavy favorite
    spot = t[(t.my_def_bad_pct >= 2 / 3) & (t.opp_off_pct >= 2 / 3) & (t.exp_margin <= -HEAVY_FAV)]
    res.append(summarize(spot[spot.dst_week & spot.travelling], "C1 Weak pass D dog travelling, clock-change week"))
    res.append(summarize(spot[spot.dst_week & ~spot.travelling], "C2 Weak pass D dog at home, clock-change week"))
    res.append(summarize(spot[~spot.dst_week & spot.travelling], "C3 Weak pass D dog travelling, other weeks"))
    res.append(summarize(spot[~spot.dst_week & ~spot.travelling], "C4 Weak pass D dog at home, other weeks"))
    # Same spot, wider window (clock-change week and the week after) to grow the sample
    wide = spot.days_after_fb.between(0, 13)
    res.append(summarize(spot[wide & spot.travelling], "C5 Weak pass D dog travelling, 2 weeks after change"))
    # 4. Consistency check: split seasons
    for lab, cond in [("1999-2012", trav.season <= 2012), ("2013-2026", trav.season >= 2013)]:
        res.append(summarize(trav[trav.dst_week & cond], f"D Travelling, clock-change week, {lab}"))
    r = pd.DataFrame(res)
    r.to_csv(os.path.join(OUT, "dst_travel_summary.csv"), index=False)
    spot[spot.dst_week].sort_values("gameday").to_csv(os.path.join(OUT, "dst_spot_games.csv"), index=False)
    pd.set_option("display.width", 220)
    print(r.to_string(index=False))
    print("\nlabel coverage:", t.my_def_bad_pct.notna().mean().round(3))


if __name__ == "__main__":
    main()
