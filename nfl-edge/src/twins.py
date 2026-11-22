"""Game twins: for any game, past or upcoming, list the past games that looked
the most like it, player by player and condition by condition.

Three separate searches, never blended:
  pass cell  this offense's QB/WR/TE/OT vs this defense's EDGE/DL/CB/S/LB
  run cell   this offense's RB and line vs this defense's front
  whole game both teams' cells at once, plus the setting (travel, body clock,
             rest, weather, roof, week, clock change, primetime)
Only games played BEFORE the target game can be twins. Each twin is listed on
its own line with the players involved and what actually happened.

Usage:
  python src/twins.py 2026_13_SF_NYG          (upcoming or past game id)
  python src/twins.py --all-upcoming          (every game not yet played)
"""
import os, sys
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(ROOT, "data", "processed")
OUTD = os.path.join(ROOT, "results", "twins")

PASS = (["off_QB1_" + t for t in ["epa_per_dropback", "accuracy_cpoe", "deep_epa", "under_pressure_epa",
                                   "clean_pocket_epa", "sack_avoidance", "ball_security", "third_down_epa"]]
        + [f"off_WR{i}_{t}" for i in (1, 2, 3) for t in ["epa_per_target", "deep_epa", "catch_rate"]]
        + ["off_TE1_epa_per_target"]
        + [f"off_OT{i}_{t}" for i in (1, 2) for t in ["unit_pressure_allowed", "unit_sacks_allowed", "holding_rate"]]
        + [f"def_EDGE{i}_{t}" for i in (1, 2) for t in ["pressure_rate", "sack_rate", "qb_hit_rate"]]
        + [f"def_DL{i}_{t}" for i in (1, 2) for t in ["pressure_rate", "sack_rate"]]
        + [f"def_CB{i}_{t}" for i in (1, 2, 3) for t in ["yards_per_target", "rating_allowed", "ball_skills"]]
        + [f"def_S{i}_{t}" for i in (1, 2) for t in ["yards_per_target", "ball_skills"]]
        + ["def_LB1_rating_allowed", "def_LB1_yards_per_target"])
RUN = (["off_RB1_" + t for t in ["rush_epa", "rush_success", "explosive_runs", "yards_after_contact",
                                  "broken_tackles", "third_down_rush_success"]]
       + [f"off_OT{i}_unit_run_epa" for i in (1, 2)] + [f"off_IOL{i}_unit_run_epa" for i in (1, 2, 3)]
       + ["off_QB1_rushing_epa"]
       + [f"def_DL{i}_{t}" for i in (1, 2) for t in ["run_stop_tfl", "tackles"]]
       + [f"def_EDGE{i}_run_stop_tfl" for i in (1, 2)]
       + [f"def_LB{i}_{t}" for i in (1, 2) for t in ["tackles", "run_stop_tfl", "missed_tackle_rate"]]
       + ["def_S1_tackles", "def_S1_run_stop_tfl"])
# Setting: (column, scale) so a difference of `scale` counts like 100 grade points
SETTING = [("off_home", 1), ("neutral", 1), ("off_zones_travelled", 3), ("def_zones_travelled", 3),
           ("off_body_clock_hour", 6), ("def_body_clock_hour", 6), ("rest_diff", 7), ("is_dome", 1),
           ("temp_f", 50), ("wind_f", 20), ("primetime", 1), ("week", 17), ("days_after_clock_change", 60),
           ("off_QB1_age", 15), ("off_QB1_exp_years", 15)]
SHOW = {"pass": [("QB1", "epa_per_dropback"), ("WR1", "epa_per_target"), ("OT1", "unit_pressure_allowed"),
                 ("EDGE1", "pressure_rate"), ("CB1", "yards_per_target")],
        "run": [("RB1", "rush_epa"), ("IOL1", "unit_run_epa"), ("DL1", "run_stop_tfl"), ("LB1", "tackles")]}


def load():
    c = pd.read_parquet(os.path.join(PROC, "game_cells.parquet"))
    c["rest_diff"] = c.off_rest - c.def_rest
    c["is_dome"] = c.roof.isin(["dome", "closed"]).astype(float)
    c["temp_f"] = c.temp.where(c.is_dome == 0, 70).fillna(60)
    c["wind_f"] = c.wind.where(c.is_dome == 0, 0).fillna(5)
    for b in ["off_home", "neutral", "primetime"]:
        c[b] = c[b].astype(float)
    c["gd"] = pd.to_datetime(c.gameday)
    return c


def upcoming_cell(c, gid):
    """Build an unplayed game's cells from each team's most recent lineup and grades."""
    rows = c[c.game_id == gid].copy()
    played = c[c.off_points.notna()]
    for i, r in rows.iterrows():
        for side, team in [("off_", r.offense), ("def_", r.defense)]:
            key = "offense" if side == "off_" else "defense"
            last = played[(played[key] == team) & (played.gd < r.gd)].sort_values("gd").tail(1)
            if len(last):
                cols = [x for x in c.columns if x.startswith(side) and x not in
                        ("off_home", "off_rest", "def_rest", "off_coach", "def_coach", "off_points", "def_points",
                         "off_zones_travelled", "def_zones_travelled", "off_body_clock_hour", "def_body_clock_hour")]
                rows.loc[i, cols] = last.iloc[0][cols].values
        recent = played[(played.offense == r.offense) & (played.gd < r.gd)].sort_values("gd").tail(RECENT_GAMES)
        for role, n, usage in USAGE_ROLES:
            reslot(rows, i, recent, role, n, usage)
    return rows


# Skill-position slots for an unplayed game: ranked by each player's actual volume over the team's
# last few games, within his own position (WR with WRs, TE with TEs), not by one game or by rating
RECENT_GAMES = 4
USAGE_ROLES = [("WR", 3, "targets"), ("TE", 1, "targets"), ("RB", 1, "carries")]
_PG = None


def _usage():
    global _PG
    if _PG is None:
        _PG = pd.read_parquet(os.path.join(PROC, "player_games.parquet"),
                              columns=["game_id", "player_id", "team", "targets", "carries"])
    return _PG


def reslot(rows, i, recent, role, n, usage):
    if recent.empty:
        return
    slots = sorted({int(x[len(f"off_{role}"):].split("_")[0]) for x in recent.columns
                    if x.startswith(f"off_{role}") and x.endswith("_player_id")})
    latest = {}                                   # player -> his slot fields from his most recent game
    for _, g in recent.iterrows():
        for k in slots:
            pid = g.get(f"off_{role}{k}_player_id")
            if pd.notna(pid):
                pre = f"off_{role}{k}_"
                latest[pid] = {x[len(pre):]: g[x] for x in recent.columns if x.startswith(pre)}
    if not latest:
        return
    pg = _usage()
    vol = pg[pg.game_id.isin(recent.game_id) & pg.player_id.isin(list(latest))].groupby("player_id")[usage].sum()
    order = sorted(latest, key=lambda p: -float(vol.get(p, 0) or 0))[:n]
    for k in slots:
        for x in [c for c in rows.columns if c.startswith(f"off_{role}{k}_")]:
            rows.loc[i, x] = np.nan
    for k, pid in enumerate(order, 1):
        for f, v in latest[pid].items():
            col = f"off_{role}{k}_{f}"
            if col in rows.columns:
                rows.loc[i, col] = v


WEIGHTS = None


def use_learned_weights():
    """Weight each grading point by how much it lined up with results in 2018-2022 (see learn_weights.py)."""
    global WEIGHTS
    w = pd.read_csv(os.path.join(PROC, "feature_weights.csv"))
    WEIGHTS = dict(zip(w.feature, w.weight))


def dist(target, pool, feats, setting=False):
    if setting:
        cols = [f for f, _ in feats]
        scale = np.array([s for _, s in feats], dtype=float)
    else:
        cols = [f for f in feats if f in pool]
        scale = np.full(len(cols), 100.0)
    t = pd.to_numeric(target[cols], errors="coerce").values.astype(float)
    P = pool[cols].apply(pd.to_numeric, errors="coerce").values.astype(float)
    d = np.abs(P - t) / scale
    have = ~np.isnan(d)
    need = (~np.isnan(t)).sum()
    cover = have.sum(1) / max(need, 1)
    if WEIGHTS is not None and not setting:
        w = np.array([WEIGHTS.get(f, 0.0) for f in cols]) + 1e-3
        dd = np.where(have, np.minimum(d, 1), 0) * w
        mean = dd.sum(1) / np.where(have, w, 0).sum(1).clip(1e-9)
    else:
        mean = np.nanmean(np.where(have, np.minimum(d, 1), np.nan), axis=1)
    out = np.where(cover >= 0.5, mean, np.nan)
    return pd.Series(out, index=pool.index), need


def fmt_players(r, cell):
    parts = []
    for role, t in SHOW[cell]:
        side = "off_" if role in ("QB1", "WR1", "OT1", "RB1", "IOL1") else "def_"
        n = r.get(f"{side}{role}_player_display_name")
        v = r.get(f"{side}{role}_{t}")
        if isinstance(n, str):
            parts.append(f"{n} {v:.0f}" if pd.notna(v) else n)
    return ", ".join(parts)


def cell_lines(target, pool, cell, feats, n=15):
    d, need = dist(target, pool, feats)
    top = pool.assign(_d=d).dropna(subset=["_d"]).nsmallest(n, "_d")
    res = "result_pass_epa_per_play" if cell == "pass" else "result_rush_epa_per_play"
    lines = [f"| Similarity | Game | Offense vs defense | Players (grade going in) | {cell.title()} EPA/play | Points | vs line |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for _, r in top.iterrows():
        sim = 100 * (1 - r._d)
        vs = "" if pd.isna(r.result_vs_line) else f"{r.result_vs_line:+.1f}"
        lines.append(f"| {sim:.0f} | {r.gameday} wk{r.week} | {r.offense} vs {r.defense} | {fmt_players(r, cell)} | "
                     f"{r[res]:+.2f} | {r.off_points:.0f}-{r.def_points:.0f} | {vs} |")
    return lines, need


_INJ = None


def injury_tag(name, season, week):
    """Latest injury report status for a player name in that season, up to that week."""
    global _INJ
    if _INJ is None:
        import glob
        f = os.path.join(ROOT, "data/raw/injuries")
        _INJ = pd.concat([pd.read_csv(x) for x in glob.glob(f + "/*.csv")], ignore_index=True)
    if not isinstance(name, str):
        return ""
    x = _INJ[(_INJ.season == season) & (_INJ.week <= week) & (_INJ.week >= week - 1) & (_INJ.full_name == name)]
    if len(x) == 0:
        return ""
    st = x.sort_values("week").iloc[-1].report_status
    return f" ({st.upper()})" if isinstance(st, str) else ""


def matchup_table(r):
    pairs = [("QB1", "EDGE1", "under_pressure_epa", "pressure_rate"), ("OT1", "EDGE1", "unit_pressure_allowed", "pressure_rate"),
             ("OT2", "EDGE2", "unit_pressure_allowed", "pressure_rate"), ("WR1", "CB1", "epa_per_target", "yards_per_target"),
             ("WR2", "CB2", "epa_per_target", "yards_per_target"), ("WR3", "CB3", "epa_per_target", "yards_per_target"),
             ("TE1", "S1", "epa_per_target", "yards_per_target"), ("RB1", "LB1", "rush_epa", "tackles"),
             ("IOL1", "DL1", "unit_run_epa", "run_stop_tfl")]
    lines = [f"**{r.offense} offense vs {r.defense} defense**" + (" (injury tags from the latest report)" if pd.isna(r.off_points) else ""), "",
             "| Offense player | Grade | Defense player | Grade | Edge |", "| --- | --- | --- | --- | --- |"]
    for o, dfn, ot, dt_ in pairs:
        on, ov = r.get(f"off_{o}_player_display_name"), r.get(f"off_{o}_{ot}")
        dn, dv = r.get(f"def_{dfn}_player_display_name"), r.get(f"def_{dfn}_{dt_}")
        if not isinstance(on, str) and not isinstance(dn, str):
            continue
        edge = "" if pd.isna(ov) or pd.isna(dv) else f"{ov - dv:+.0f}"
        f = lambda v: "" if pd.isna(v) else f"{v:.0f}"
        oi = injury_tag(on, r.season, r.week) if pd.isna(r.off_points) else ""
        di = injury_tag(dn, r.season, r.week) if pd.isna(r.off_points) else ""
        lines.append(f"| {o} {on or ''}{oi} ({ot}) | {f(ov)} | {dfn} {dn or ''}{di} ({dt_}) | {f(dv)} | {edge} |")
    return lines + [""]


def whole_game(tg, pool, n=20):
    """Both cells plus the setting, matched as a pair. Returns the n closest past games."""
    home = tg[tg.off_home == 1].iloc[0] if (tg.off_home == 1).any() else tg.iloc[0]
    away = tg[tg.offense != home.offense].iloc[0]
    ph = pool[pool.off_home == 1].set_index("game_id")
    ph = ph[~ph.index.duplicated()]
    pa = pool[pool.off_home == 0].set_index("game_id")
    pa = pa[~pa.index.duplicated()].reindex(ph.index)
    d1, _ = dist(home, ph, PASS + RUN)
    d2, _ = dist(away, pa, PASS + RUN)
    d3, _ = dist(home, ph, SETTING, setting=True)
    tot = (d1 + d2 + d3) / 3
    top = ph.assign(_d=tot, _a=pa.offense, _ap=pa.off_points).dropna(subset=["_d"]).nsmallest(n, "_d")
    return home, away, top, pa


def report(gid, c=None):
    c = load() if c is None else c
    tg = c[c.game_id == gid]
    if tg.off_points.isna().all():
        tg = upcoming_cell(c, gid)
    gd = tg.gd.iloc[0]
    pool = c[(c.gd < gd) & c.off_points.notna()]
    first = tg.iloc[0]
    L = [f"# Game twins: {gid}", "",
         f"{first.gameday}, {first.stadium}. Kickoff {first.kickoff_ET} ET. Roof: {first.roof}. "
         f"{'Unplayed: lineups and grades taken from each team''s most recent game.' if pd.isna(first.off_points) else ''}", "",
         "Grades are 0-100 going into the game (50 = average at the position that season). "
         "Similarity 100 = identical. Only earlier games are searched.", ""]
    for _, r in tg.iterrows():
        L += matchup_table(r)
    for _, r in tg.iterrows():
        for cell, feats in [("pass", PASS), ("run", RUN)]:
            lines, need = cell_lines(r, pool[pool.game_type.notna()], cell, feats)
            L += [f"## {r.offense} {cell} offense vs {r.defense} {cell} defense: closest past matchups", "",
                  f"Matched on {need} player grading points.", ""] + lines + [""]
    home, away, top, pa = whole_game(tg, pool)
    L += [f"## Whole-game twins: {away.offense} at {home.offense}", "",
          "Both teams' player matchups and the setting matched at once.", "",
          "| Similarity | Game | Home QB vs Away QB | Setting | Score (home-away) | Home vs line |",
          "| --- | --- | --- | --- | --- | --- |"]
    for gid2, r in top.iterrows():
        aq = pa.loc[gid2, "off_QB1_player_display_name"]
        setting = f"{r.roof}, {'' if pd.isna(r.temp) else f'{r.temp:.0f}F, '}wk{r.week}, away body clock {pa.loc[gid2, 'off_body_clock_hour']:.0f}:00"
        vs = "" if pd.isna(r.result_vs_line) else f"{r.result_vs_line:+.1f}"
        L.append(f"| {100 * (1 - r._d):.0f} | {r.gameday} {r._a} at {r.offense} | {r.off_QB1_player_display_name} vs {aq} | "
                 f"{setting} | {r.off_points:.0f}-{r._ap:.0f} | {vs} |")
    W = (top.off_points > top._ap).sum()
    L += ["", f"In these 20 twins the home side won {W} and lost {len(top) - W}. Each game above is its own data point.", ""]
    os.makedirs(OUTD, exist_ok=True)
    path = os.path.join(OUTD, f"{gid}.md")
    open(path, "w").write("\n".join(L))
    return path


if __name__ == "__main__":
    c = load()
    if sys.argv[1] == "--all-upcoming":
        ids = c[c.off_points.isna()].sort_values("gd").game_id.unique()
        for gid in ids:
            try:
                print(report(gid, c))
            except Exception as e:
                print("skip", gid, e)
    else:
        print(report(sys.argv[1], c))
