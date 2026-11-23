"""Trait-by-trait game matching.

Every past game (one row per offense-vs-defense side) is profiled on ~40
separate attributes: offensive units, defensive units, and the game setting.
An upcoming game is "plugged in" and each past game is scored by HOW MANY
attributes match, each checked on its own tolerance. Nothing is blended.
Every attribute that does not match is listed with what it could change.

Offensive line (and pass rush / coverage) ratings come from Madden player
cards (2001+) so old seasons are graded on the same scale as new ones.
Production grades (EPA etc.) come from the nflverse play-by-play grades.

Build the database:   python src/trait_match.py build
Plug in a game:       python src/trait_match.py match 2026_11_CIN_WAS WAS [--temp 54 --wind 8] [--top 5]
"""
import sys, os, argparse, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import pandas as pd
import twins

ROOT = os.path.join(os.path.dirname(__file__), "..")
DB = os.path.join(ROOT, "data/processed/game_traits.parquet")
OL = ["OT1", "OT2", "IOL1", "IOL2", "IOL3"]
DEF = ["EDGE1", "EDGE2", "DL1", "DL2", "LB1", "LB2", "CB1", "CB2", "CB3", "S1", "S2"]

# ---------------------------------------------------------------- attributes
# Each attribute: (name, db column, tolerance, kind, what a mismatch affects, meaning of a HIGHER value tonight)
# kind: num -> match if |tonight - then| <= tolerance ; exact -> equal
MT = 5      # Madden ratings (0-99): within 5 points
PT = 15     # production grades (0-100 percentile): within 15 points

# Madden units: unit -> (cell slots, Madden position groups/positions for teams with no slot data, how many starters)
UNITS = {
    "OL": (["off_OT1", "off_OT2", "off_IOL1", "off_IOL2", "off_IOL3"], ("o_line", None), 5),
    "OT": (["off_OT1", "off_OT2"], ("o_line", {"T", "LT", "RT"}), 2),
    "IOL": (["off_IOL1", "off_IOL2", "off_IOL3"], ("o_line", {"G", "C", "LG", "RG"}), 3),
    "LT": (["off_OT1"], ("o_line", {"T", "LT", "OL"}), 1),
    "C": (["off_IOL1"], ("o_line", {"C"}), 1),
    "QB": (["off_QB1"], ("quarterback", None), 1),
    "RB": (["off_RB1"], ("o_rush", None), 1),
    "WR1": (["off_WR1"], ("o_pass", None), 1),
    "WR2": (["off_WR2"], ("o_pass", "2nd"), 1),
    "WRS": (["off_WR1", "off_WR2", "off_WR3"], ("o_pass", None), 3),
    "TE": (["off_TE1"], ("o_te", {"TE"}), 1),
    "DL": (["def_EDGE1", "def_EDGE2", "def_DL1", "def_DL2"], ("d_line", None), 4),
    "EDGE": (["def_EDGE1", "def_EDGE2"], ("d_line", {"DE"}), 2),
    "IDL": (["def_DL1", "def_DL2"], ("d_line", {"DT", "NT"}), 2),
    "LB": (["def_LB1", "def_LB2"], ("d_lb", None), 2),
    "CB": (["def_CB1", "def_CB2", "def_CB3"], ("d_field", {"CB"}), 3),
    "S": (["def_S1", "def_S2"], ("d_field", {"FS", "SS", "S"}), 2),
}
MADDEN = [  # (unit, Madden field, label, affects, higher)
    ("OL", "m_passblock", "OL pass blocking", "sacks, pressure, QB passing", "better pass protection"),
    ("OL", "m_passblockpower", "OL pass block power (bull rush)", "sacks vs power rushers", "anchors better"),
    ("OL", "m_passblockfinesse", "OL pass block finesse (speed rush)", "sacks vs speed rushers", "handles speed better"),
    ("OL", "m_runblock", "OL run blocking", "RB rushing yards", "better run blocking"),
    ("OL", "m_runblockpower", "OL run block power (gap/drive)", "short-yardage, RB yards", "more push"),
    ("OL", "m_runblockfinesse", "OL run block finesse (zone)", "zone runs, RB yards", "better zone blocking"),
    ("OL", "m_impactblocking", "OL impact blocking", "RB explosive runs", "more knock-back"),
    ("OL", "m_strength", "OL strength", "run game, power rush", "stronger"),
    ("OL", "m_awareness", "OL awareness", "blitz pickup, penalties", "smarter line"),
    ("OL", "m_agility", "OL agility (pulling/screens)", "screens, outside runs", "more mobile line"),
    ("OT", "m_passblock", "Tackles pass blocking", "edge sacks, pressure", "better tackles in pass pro"),
    ("OT", "m_passblockfinesse", "Tackles vs speed rush", "edge sacks", "handle speed better"),
    ("OT", "m_runblock", "Tackles run blocking", "outside runs", "better run-blocking tackles"),
    ("IOL", "m_passblock", "Guards/center pass blocking", "interior pressure, sacks up the middle", "better interior pass pro"),
    ("IOL", "m_passblockpower", "Guards/center vs bull rush", "interior pressure", "anchor better"),
    ("IOL", "m_runblock", "Guards/center run blocking", "inside runs", "better interior run blocking"),
    ("IOL", "m_runblockpower", "Guards/center drive blocking", "short yardage, inside runs", "more interior push"),
    ("LT", "m_passblock", "Left tackle pass blocking (blind side)", "sacks, strip-sacks", "better blind-side tackle"),
    ("C", "m_awareness", "Center awareness (line calls)", "blitz pickup", "smarter center"),
    ("QB", "m_throwpower", "QB arm strength", "deep passing yards", "stronger arm"),
    ("QB", "m_throwaccuracyshort", "QB short accuracy", "completions", "more accurate short"),
    ("QB", "m_throwaccuracymid", "QB mid accuracy", "passing yards", "more accurate mid"),
    ("QB", "m_throwaccuracydeep", "QB deep accuracy", "big plays", "more accurate deep"),
    ("QB", "m_throwonrun", "QB throwing on the run", "broken plays", "better on the move"),
    ("QB", "m_speed", "QB speed", "QB rushing yards", "faster QB"),
    ("QB", "m_awareness", "QB awareness", "INTs, sacks", "smarter QB"),
    ("RB", "m_speed", "RB speed", "long runs", "faster back"),
    ("RB", "m_elusiveness", "RB elusiveness", "missed tackles, RB yards", "shiftier"),
    ("RB", "m_trucking", "RB power (trucking)", "yards after contact, short yardage", "more power"),
    ("RB", "m_bcvision", "RB vision", "RB rushing yards", "better vision"),
    ("RB", "m_carrying", "RB ball security", "fumbles", "holds on better"),
    ("RB", "m_catching", "RB hands", "RB receptions", "better hands"),
    ("RB", "m_passblock", "RB pass blocking", "sacks, 3rd-down usage", "blocks better"),
    ("WR1", "m_speed", "WR1 speed", "WR1 deep yards", "faster WR1"),
    ("WR1", "m_catching", "WR1 hands", "WR1 catches", "better hands"),
    ("WR1", "m_routerunning", "WR1 route running", "WR1 targets/catches", "better routes"),
    ("WR1", "m_release", "WR1 release vs press", "WR1 vs press corners", "beats press better"),
    ("WR1", "m_catchintraffic", "WR1 catch in traffic", "WR1 contested catches", "wins in traffic"),
    ("WR2", "m_speed", "WR2 speed", "WR2 yards", "faster WR2"),
    ("WR2", "m_catching", "WR2 hands", "WR2 catches", "better hands"),
    ("WRS", "m_runblock", "WR run blocking (WR1-3)", "RB outside runs", "receivers block better"),
    ("TE", "m_catching", "TE hands", "TE catches", "better hands"),
    ("TE", "m_speed", "TE speed", "TE yards after catch / seams", "faster TE"),
    ("TE", "m_runblock", "TE run blocking", "run game", "better blocking TE"),
    ("TE", "m_passblock", "TE pass blocking", "protection", "better pass-pro TE"),
    ("EDGE", "m_finessemoves", "Edge speed-rush moves", "sacks, QB under pressure", "better speed rushers"),
    ("EDGE", "m_powermoves", "Edge power moves", "sacks, pressure", "better power rushers"),
    ("EDGE", "m_speed", "Edge speed", "sacks, QB scrambles contained", "faster edges"),
    ("IDL", "m_powermoves", "Interior DL power moves", "interior pressure", "more interior push"),
    ("IDL", "m_blockshedding", "Interior DL block shedding", "RB rushing yards", "sheds blocks better"),
    ("IDL", "m_strength", "Interior DL strength", "RB rushing yards", "stronger interior"),
    ("DL", "m_tackle", "DL tackling", "RB yards after contact", "surer tacklers"),
    ("LB", "m_tackle", "LB tackling (Madden)", "RB yards after contact", "surer tacklers"),
    ("LB", "m_pursuit", "LB pursuit", "RB outside runs, screens", "better pursuit"),
    ("LB", "m_playrecognition", "LB play recognition", "play action, misdirection", "reads plays better"),
    ("LB", "m_zonecoverage", "LB zone coverage", "TE/RB receiving", "better in coverage"),
    ("LB", "m_speed", "LB speed", "QB scrambles, RB outside runs", "faster LBs"),
    ("CB", "m_mancoverage", "CB man coverage", "WR receiving yards", "better man corners"),
    ("CB", "m_zonecoverage", "CB zone coverage", "WR receiving yards", "better zone corners"),
    ("CB", "m_press", "CB press", "WR releases, timing routes", "better press"),
    ("CB", "m_speed", "CB speed", "deep passes", "faster corners"),
    ("CB", "m_catching", "CB hands (INTs)", "interceptions", "better hands"),
    ("S", "m_zonecoverage", "Safety zone coverage", "deep passes, TE seams", "better cover safeties"),
    ("S", "m_hitpower", "Safety hit power", "fumbles, contested catches", "bigger hitters"),
    ("S", "m_speed", "Safety speed", "deep passes", "faster safeties"),
]
PROD = [  # (db col, cell cols averaged, label, tol, affects, higher)
    ("ol_sacks_prod", ["off_OT1_unit_sacks_allowed", "off_OT2_unit_sacks_allowed"], "OL sacks allowed (production)", PT, "sacks", "allows fewer sacks"),
    ("ol_press_prod", ["off_OT1_unit_pressure_allowed", "off_OT2_unit_pressure_allowed"], "OL pressure allowed (production)", PT, "pressure, QB passing", "allows less pressure"),
    ("ol_run_prod", ["off_%s_unit_run_epa" % x for x in ["OT1", "OT2", "IOL1", "IOL2", "IOL3"]], "OL run blocking (production)", PT, "RB rushing yards", "blocks the run better"),
    ("ol_holding", ["off_%s_holding_rate" % x for x in ["OT1", "OT2", "IOL1", "IOL2", "IOL3"]], "OL holding penalties (higher = cleaner)", PT, "drive-killing penalties", "cleaner line"),
    ("ol_falsestart", ["off_%s_false_start_rate" % x for x in ["OT1", "OT2", "IOL1", "IOL2", "IOL3"]], "OL false starts (higher = cleaner)", PT, "penalties on the road", "cleaner line"),
    ("ol_age", ["off_%s_age" % x for x in ["OT1", "OT2", "IOL1", "IOL2", "IOL3"]], "OL age", 2, "", "older line"),
    ("ol_exp", ["off_%s_exp_years" % x for x in ["OT1", "OT2", "IOL1", "IOL2", "IOL3"]], "OL experience (years)", 2, "blitz pickup", "more experienced line"),
    ("qb_pass", ["off_QB1_epa_per_dropback"], "QB passing (production)", PT, "QB passing yards / TDs", "better passer"),
    ("qb_run", ["off_QB1_rushing_epa"], "QB running (production)", PT, "QB rushing yards", "more of a runner"),
    ("qb_pressure", ["off_QB1_under_pressure_epa"], "QB under pressure", PT, "sacks, INTs", "handles pressure better"),
    ("qb_deep", ["off_QB1_deep_epa"], "QB deep passing (production)", PT, "big plays", "better deep"),
    ("qb_third", ["off_QB1_third_down_epa"], "QB on third down", PT, "drives sustained", "better on 3rd down"),
    ("qb_ballsec", ["off_QB1_ball_security"], "QB ball security", PT, "INTs, fumbles", "protects ball better"),
    ("qb_primetime", ["off_QB1_primetime_epa"], "QB in primetime", PT, "night-game passing", "better at night"),
    ("qb_age", ["off_QB1_age"], "QB age", 3, "", "older QB"),
    ("qb_exp", ["off_QB1_exp_years"], "QB experience (years)", 2, "big-spot mistakes", "more experienced"),
    ("rb_run", ["off_RB1_rush_epa"], "RB running (production)", PT, "RB rushing yards", "better runner"),
    ("rb_success", ["off_RB1_rush_success"], "RB run success rate", PT, "RB rushing yards", "more consistent"),
    ("rb_explosive", ["off_RB1_explosive_runs"], "RB explosive runs", PT, "long runs", "more explosive"),
    ("rb_yac", ["off_RB1_yards_after_contact"], "RB yards after contact (production)", PT, "RB rushing yards", "breaks more tackles"),
    ("rb_catch", ["off_RB1_receiving_epa"], "RB pass catching (production)", PT, "RB receiving", "catches more"),
    ("rb_age", ["off_RB1_age"], "RB age", 2, "", "older back"),
    ("wr1_eff", ["off_WR1_epa_per_target"], "WR1 efficiency (production)", PT, "WR1 receiving yards", "better WR1"),
    ("wr1_share", ["off_WR1_target_share"], "WR1 target share", PT, "WR1 targets", "WR1 gets more of the ball"),
    ("wr1_deep", ["off_WR1_deep_epa"], "WR1 deep threat (production)", PT, "WR1 big plays", "more of a deep threat"),
    ("wr1_yac", ["off_WR1_yac_per_catch"], "WR1 yards after catch", PT, "WR1 yards", "more YAC"),
    ("wr2_eff", ["off_WR2_epa_per_target"], "WR2 efficiency (one #1 or two)", PT, "WR2 yards; coverage rolled to WR1", "stronger WR2"),
    ("wr2_share", ["off_WR2_target_share"], "WR2 target share", PT, "WR2 targets", "WR2 used more"),
    ("wr3_eff", ["off_WR3_epa_per_target"], "WR3 efficiency", PT, "WR3 yards", "better WR3"),
    ("wr1_age", ["off_WR1_age"], "WR1 age", 3, "", "older WR1"),
    ("te_share", ["off_TE1_target_share"], "TE target share", PT, "TE targets", "TE used more"),
    ("te_eff", ["off_TE1_epa_per_target"], "TE efficiency (production)", PT, "TE receiving yards", "more dangerous TE"),
    ("te_snap", ["off_TE1_snap_share"], "TE snap share", PT, "TE involvement", "TE on the field more"),
    ("edge_rush", ["def_EDGE1_pressure_rate", "def_EDGE2_pressure_rate"], "Edge pressure (production)", PT, "sacks, QB passing", "more edge pressure"),
    ("edge_sack", ["def_EDGE1_sack_rate", "def_EDGE2_sack_rate"], "Edge sack rate", PT, "sacks", "more edge sacks"),
    ("dl_rush", ["def_DL1_pressure_rate", "def_DL2_pressure_rate"], "Interior DL pressure (production)", PT, "sacks", "more interior pressure"),
    ("dl_runstop", ["def_DL1_run_stop_tfl", "def_DL2_run_stop_tfl"], "Interior DL run stop (production)", PT, "RB rushing yards", "stouter interior"),
    ("edge_runstop", ["def_EDGE1_run_stop_tfl", "def_EDGE2_run_stop_tfl"], "Edge run stop (production)", PT, "RB outside runs", "edges set the edge better"),
    ("lb_tackle", ["def_LB1_tackles", "def_LB2_tackles"], "LB tackles (production)", PT, "RB yards", "LBs make more tackles"),
    ("lb_runstop", ["def_LB1_run_stop_tfl", "def_LB2_run_stop_tfl"], "LB run stop (production)", PT, "RB rushing yards", "better run-stopping LBs"),
    ("lb_missed", ["def_LB1_missed_tackle_rate", "def_LB2_missed_tackle_rate"], "LB missed tackles (higher = fewer misses)", PT, "RB yards after contact", "miss fewer tackles"),
    ("lb_cover", ["def_LB1_rating_allowed", "def_LB2_rating_allowed"], "LB coverage (production)", PT, "TE/RB receiving", "cover better"),
    ("cb_ypt", ["def_CB1_yards_per_target", "def_CB2_yards_per_target", "def_CB3_yards_per_target"], "CB yards per target (production)", PT, "WR receiving yards", "allow fewer yards"),
    ("cb_rating", ["def_CB1_rating_allowed", "def_CB2_rating_allowed", "def_CB3_rating_allowed"], "CB passer rating allowed", PT, "WR receiving, passing TDs", "allow less"),
    ("cb_ball", ["def_CB1_ball_skills", "def_CB2_ball_skills", "def_CB3_ball_skills"], "CB ball skills (production)", PT, "INTs, PBUs", "make more plays"),
    ("s_ball", ["def_S1_ball_skills", "def_S2_ball_skills"], "Safety ball skills", PT, "INTs, deep passes", "ballhawk safeties"),
    ("s_tackle", ["def_S1_tackles", "def_S2_tackles"], "Safety tackling", PT, "RB long runs", "better tackling safeties"),
    ("def_age", ["def_%s_age" % x for x in ["EDGE1", "EDGE2", "DL1", "DL2", "LB1", "LB2", "CB1", "CB2", "CB3", "S1", "S2"]], "Defense age", 1.5, "", "older defense"),
    ("def_exp", ["def_%s_exp_years" % x for x in ["EDGE1", "EDGE2", "DL1", "DL2", "LB1", "LB2", "CB1", "CB2", "CB3", "S1", "S2"]], "Defense experience", 1.5, "", "more experienced defense"),
]
CONTEXT = [
    ("Home / away", "off_home", 0, "exact", "everything", ""),
    ("Game slot (MNF / SNF / TNF / day)", "slot", 0, "exact", "primetime performance", ""),
    ("Week of season", "week", 2, "num", "late-season form", "later in season"),
    ("Offense rest days", "off_rest", 1, "num", "", "more rest"),
    ("Offense off a bye", "off_bye", 0, "exact", "", ""),
    ("Offense on a short week", "off_short", 0, "exact", "", ""),
    ("Defense rest days", "def_rest", 1, "num", "", "more rest"),
    ("Defense off a bye", "def_bye", 0, "exact", "", ""),
    ("Defense on a short week", "def_short", 0, "exact", "", ""),
    ("Time zones the offense travelled", "off_zones_travelled", 1, "num", "body clock", "travelled further"),
    ("Time zones the defense travelled", "def_zones_travelled", 1, "num", "body clock", "travelled further"),
    ("Dome / outdoors", "is_dome", 0, "exact", "passing, kicking", ""),
    ("Temperature (F)", "temp_f", 12, "num", "passing, ball security", "warmer"),
    ("Wind (mph)", "wind_f", 7, "num", "deep passing, kicking", "windier"),
    ("Grass / turf", "grass", 0, "exact", "speed", ""),
    ("Division game", "div_game", 0, "exact", "familiarity, lower scoring", ""),
    ("WR carries (WR1-3 runs, prior 4 games)", "wr_carries", 1, "num", "WR rushing, gadget plays", "receivers get more carries"),
]
ATTRS = ([(lab, f"md_{u}_{f[2:]}", MT, "num", aff, hi) for u, f, lab, aff, hi in MADDEN]
         + [(lab, col, tol, "num", aff, hi) for col, _, lab, tol, aff, hi in PROD]
         + CONTEXT)
TEAMMAP = {"STL": "LAR", "LA": "LAR", "SD": "LAC", "OAK": "LV"}


def _mean(df, cols):
    cols = [c for c in cols if c in df]
    return df[cols].apply(pd.to_numeric, errors="coerce").mean(axis=1)


def _slot(weekday, kick):
    h = pd.to_numeric(str(kick)[:2], errors="coerce") if isinstance(kick, str) else np.nan
    if weekday == "Monday":
        return "MNF"
    if weekday == "Thursday":
        return "TNF"
    if weekday == "Sunday" and h is not None and h >= 19:
        return "SNF"
    if weekday == "Sunday":
        return "Sun day"
    return weekday


def madden_lookup():
    m = pd.read_parquet(os.path.join(ROOT, "data/processed/madden_ratings.parquet"))
    m = m[m.m_overall.notna()].copy()
    m["m_routerunning"] = m["m_routerunning"].fillna(
        m[["m_shortrouterunning", "m_midrouterunning", "m_deeprouterunning"]].mean(axis=1))
    m["team"] = m.team.replace(TEAMMAP)
    return m


def team_cards(m):
    """Team fallback for games with no slot lineup (mostly before 2012): each team-season's
    top Madden players at the unit, by overall rating."""
    fields = sorted({f for _, f, *_ in MADDEN})
    rows = {}
    for u, (_, (grp, pos), n) in UNITS.items():
        x = m[m.position_group == grp]
        if isinstance(pos, set):
            sub = x[x.position.isin(pos)]
            x = sub if len(sub) else x
        x = x.sort_values("m_overall", ascending=False)
        x = x.assign(_r=x.groupby(["season", "team"]).cumcount())
        x = x[(x._r == 1)] if pos == "2nd" else x[x._r < n]
        rows[u] = x.groupby(["season", "team"])[fields].mean()
    return rows


def attach_madden(c, m):
    """Unit Madden ratings per game: the players in the lineup slots (that season's card,
    else the season before); if the game has no slot lineup, the team's top Madden starters."""
    fields = sorted({f for _, f, *_ in MADDEN})
    cards = m.dropna(subset=["player_id"]).drop_duplicates(["player_id", "season"], keep="last").set_index(["player_id", "season"])[fields]
    tc = team_cards(m)
    out = {}
    cache = {}
    wk = (pd.to_numeric(c.week, errors="coerce").clip(1, 18) / 18.0).values[:, None]
    def slot_vals(slot):
        """Game-time rating. The launch card for season s was set from season s-1; the
        next edition (s+1) was set from season s itself. So a week-w game gets
        launch(s) + (next(s+1) - launch(s)) * w/18. If the next edition does not exist
        yet (current season) the in-season update card is used as is; if the player has
        no card for s, the s+1 card (or the s-1 card) is used."""
        if slot in cache:
            return cache[slot]
        pid = c[f"{slot}_player_id"].values
        get = lambda yr: cards.reindex(pd.MultiIndex.from_arrays([pid, yr])).reset_index(drop=True)
        now_ = get(c.season.values); nxt = get((c.season + 1).values); prv = get((c.season - 1).values)
        v = now_ + (nxt - now_) * wk
        v = v.fillna(now_).fillna(nxt).fillna(prv)
        v.index = c.index
        cache[slot] = v
        return v
    for u, (slots, _, _) in UNITS.items():
        unit = sum(slot_vals(s).fillna(0) for s in slots)
        cnt = sum(slot_vals(s).notna().astype(int) for s in slots)
        unit = unit / cnt.replace(0, np.nan)
        side = "offense" if slots[0].startswith("off") else "defense"
        team = c[side].replace(TEAMMAP)
        key = pd.MultiIndex.from_arrays([c.season.values, team.values])
        fb = tc[u].reindex(key).reset_index(drop=True)
        fb.index = c.index
        unit = unit.fillna(fb)
        for f in fields:
            if any(uu == u and ff == f for uu, ff, *_ in MADDEN):
                out[f"md_{u}_{f[2:]}"] = unit[f]
    return pd.DataFrame(out, index=c.index)


def wr_carries(c):
    """WR1-3 carries over each offense's previous 4 games (role, not result)."""
    pg = pd.read_parquet(os.path.join(ROOT, "data/processed/player_games.parquet"),
                         columns=["game_id", "team", "position", "carries"])
    w = pg[pg.position == "WR"].groupby(["game_id", "team"]).carries.sum().rename("wr_c").reset_index()
    g = c[["game_id", "offense", "gd"]].rename(columns={"offense": "team"}).merge(w, on=["game_id", "team"], how="left")
    g["wr_c"] = g.wr_c.fillna(0)
    g = g.sort_values("gd")
    g["prior"] = g.groupby("team").wr_c.transform(lambda s: s.shift(1).rolling(4, min_periods=1).sum())
    return g.set_index(["game_id", "team"]).prior.groupby(level=[0, 1]).last()


def profile(c, mad=None, wrc=None):
    d = pd.DataFrame(index=c.index)
    for k in ["game_id", "season", "week", "gameday", "offense", "defense", "off_points", "def_points",
              "line", "total_line", "off_home", "off_rest", "def_rest", "off_zones_travelled",
              "def_zones_travelled", "is_dome", "temp_f", "wind_f", "div_game"]:
        d[k] = c[k]
    d["slot"] = [_slot(w, k) for w, k in zip(c.weekday, c.kickoff_ET)]
    rest_o = pd.to_numeric(c.off_rest, errors="coerce"); rest_d = pd.to_numeric(c.def_rest, errors="coerce")
    d["off_bye"] = (rest_o >= 13).astype(int); d["def_bye"] = (rest_d >= 13).astype(int)
    d["off_short"] = (rest_o <= 5).astype(int); d["def_short"] = (rest_d <= 5).astype(int)
    d["grass"] = c.surface.astype(str).str.contains("grass").astype(int)
    if mad is not None:
        d = pd.concat([d, mad], axis=1)
    for col, cols, *_ in PROD:
        d[col] = _mean(c, cols)
    if wrc is not None:
        d["wr_carries"] = [wrc.get((g, t), np.nan) for g, t in zip(c.game_id, c.offense)]
    for s in ["QB1", "RB1", "WR1", "WR2", "WR3", "TE1", "OT1"]:
        d[f"{s}_name"] = c[f"off_{s}_player_display_name"]
    for s in ["EDGE1", "DL1", "LB1", "CB1", "S1"]:
        d[f"d{s}_name"] = c[f"def_{s}_player_display_name"]
    return d


def build():
    c = twins.load()
    m = madden_lookup()
    db = profile(c, attach_madden(c, m), wr_carries(c))
    db.to_parquet(DB)
    print("saved", DB, db.shape)
    for lo, hi in [(1999, 2000), (2001, 2011), (2012, 2017), (2018, 2026)]:
        x = db[(db.season >= lo) & (db.season <= hi)]
        n = np.mean([x[a[1]].notna().sum() for a in ATTRS]) / max(len(x), 1)
        print(f"{lo}-{hi}: {len(x)} games, attributes with data on average {n*len(ATTRS):.0f} of {len(ATTRS)}")
    return db


def upcoming_profile(gid, side, temp=None, wind=None):
    c = twins.load()
    tg = twins.upcoming_cell(c, gid)
    r = tg[tg.offense == side].copy()
    m = madden_lookup()
    # an upcoming game's Madden card: this season's
    d = profile(r, attach_madden(r, m), wr_carries(pd.concat([c, r])))
    if temp is not None:
        d["temp_f"] = temp
    if wind is not None:
        d["wind_f"] = wind
    return d.iloc[0]


def match(gid, side, temp=None, wind=None, top=5, weeks=None):
    db = pd.read_parquet(DB)
    now = upcoming_profile(gid, side, temp, wind)
    teams = {now.offense, now.defense}
    pool = db[db.off_points.notna() & (db.gameday < str(pd.Timestamp.today().date()))]
    pool = pool[~((pool.season == now.season) & (pool.offense.isin(teams) | pool.defense.isin(teams)))]
    hits = pd.DataFrame(index=pool.index)
    have = pd.DataFrame(index=pool.index)
    for name, col, tol, kind, *_ in ATTRS:
        v = now[col]
        if pd.isna(v):
            continue
        pv = pool[col]
        have[name] = pv.notna()
        if kind == "exact":
            hits[name] = pv == v
        else:
            hits[name] = (pd.to_numeric(pv, errors="coerce") - float(v)).abs() <= tol
    pool = pool.assign(n_match=hits.sum(1), n_have=have.sum(1))
    best = pool.sort_values(["n_match", "n_have"], ascending=False).head(top)
    return now, best, hits, have, pool


def _sign(col):
    """+1: higher helps the offense; -1: higher helps the defense; 0: neutral."""
    if col.endswith("_age") or col.endswith("_exp") or col in ("ol_age", "ol_exp", "def_age", "def_exp", "qb_age", "qb_exp", "rb_age", "wr1_age"):
        return 0
    if col.startswith("md_"):
        return -1 if col.split("_")[1] in ("EDGE", "IDL", "DL", "LB", "CB", "S") else 1
    for p in ("edge_", "dl_", "lb_", "cb_", "s_"):
        if col.startswith(p):
            return -1
    for p in ("ol_", "qb_", "rb_", "wr", "te_"):
        if col.startswith(p):
            return 1
    return 0


def explain(now, row, hits, have):
    lines = []
    for name, col, tol, kind, affects, higher in ATTRS:
        v = now[col]
        if pd.isna(v):
            lines.append((name, "no data tonight", "", "skip", ""))
            continue
        pv = row[col]
        if not have.loc[row.name, name]:
            lines.append((name, _f(v), "no data", "no data", ""))
            continue
        ok = bool(hits.loc[row.name, name])
        note = ""
        if not ok and kind == "num":
            up = float(v) > float(pv)
            sg = _sign(col)
            if sg == 0 or not affects:
                note = f"Tonight {'higher' if up else 'lower'} ({_f(v)} vs {_f(pv)})."
            else:
                good = (up and sg > 0) or (not up and sg < 0)
                note = (f"Tonight {'higher' if up else 'lower'} ({_f(v)} vs {_f(pv)}). "
                        f"Better for tonight's offense than that game: expect a better offensive result on {affects}." if good else
                        f"Tonight {'higher' if up else 'lower'} ({_f(v)} vs {_f(pv)}). "
                        f"Worse for tonight's offense than that game: expect a worse offensive result on {affects}.")
        elif not ok:
            note = f"Tonight {_f(v)}, that game {_f(pv)}. Affects {affects}."
        lines.append((name, _f(v), _f(pv), "YES" if ok else "no", note))
    return lines


def _f(x):
    if isinstance(x, (int, np.integer)) or (isinstance(x, float) and float(x).is_integer()):
        return str(int(x))
    if isinstance(x, (float, np.floating)):
        return f"{x:.1f}"
    return str(x)


def box(gid, team):
    pg = pd.read_parquet(os.path.join(ROOT, "data/processed/player_games.parquet"))
    x = pg[(pg.game_id == gid) & (pg.team == team)].fillna(0)
    out = []
    for _, q in x[(x.position == "QB") & (x.attempts > 0)].iterrows():
        out.append(f"QB {q.player_display_name}: {q.completions:.0f}/{q.attempts:.0f}, {q.passing_yards:.0f} yds, "
                   f"{q.passing_tds:.0f} TD, {q.passing_interceptions:.0f} INT, sacked {q.sacks_suffered:.0f}, "
                   f"rush {q.carries:.0f} for {q.rushing_yards:.0f}")
    for pos in ["RB", "WR", "TE"]:
        y = x[(x.position == pos) & ((x.carries > 0) | (x.targets > 0))].sort_values(["carries", "targets"], ascending=False)
        for _, p in y.iterrows():
            out.append(f"{pos} {p.player_display_name}: rush {p.carries:.0f} for {p.rushing_yards:.0f}, "
                       f"{p.rushing_tds:.0f} TD | {p.targets:.0f} targets, {p.receptions:.0f} for {p.receiving_yards:.0f}, {p.receiving_tds:.0f} TD")
    out.append(f"Defense allowed: pass {x.passing_yards.sum():.0f}, rush {x.rushing_yards.sum():.0f} on {x.carries.sum():.0f} carries, "
               f"sacks {x.sacks_suffered.sum():.0f}, INT {x.passing_interceptions.sum():.0f}, "
               f"fumbles lost {(x.rushing_fumbles_lost + x.receiving_fumbles_lost + x.sack_fumbles_lost).sum():.0f}")
    return out


def trend(gid, side):
    """Tonight's players: Madden overall over recent editions, and the position Madden lists him at."""
    c = twins.load()
    r = twins.upcoming_cell(c, gid)
    r = r[r.offense == side].iloc[0]
    m = madden_lookup()
    yrs = list(range(int(r.season) - 3, int(r.season) + 1))
    rows = []
    for slot in ["off_QB1", "off_RB1", "off_WR1", "off_WR2", "off_WR3", "off_TE1", "off_OT1", "off_OT2", "off_IOL1",
                 "off_IOL2", "off_IOL3", "def_EDGE1", "def_EDGE2", "def_DL1", "def_DL2", "def_LB1", "def_LB2",
                 "def_CB1", "def_CB2", "def_CB3", "def_S1", "def_S2"]:
        pid, nm = r.get(f"{slot}_player_id"), r.get(f"{slot}_player_display_name")
        if pd.isna(pid):
            continue
        x = m[m.player_id == pid].drop_duplicates("season", keep="last").set_index("season")
        ov = [x.m_overall.get(y, np.nan) for y in yrs]
        pos = x.position.get(int(r.season), x.position.iloc[-1] if len(x) else "?")
        v = [o for o in ov if pd.notna(o)]
        tr = "no card" if not v else ("one card" if len(v) == 1 else
              ("rising" if v[-1] - v[-2] >= 3 else "declining" if v[-2] - v[-1] >= 3 else "steady"))
        rows.append(f"| {slot.split('_')[1]} | {nm} | {pos} | " + " | ".join("-" if pd.isna(o) else f"{o:.0f}" for o in ov) + f" | {tr} |")
    head = ["| Slot | Player | Madden position | " + " | ".join(f"{y} card" for y in yrs) + " | Trend |",
            "|---|---|---|" + "---|" * (len(yrs) + 1)]
    return head + rows


def report(gid, side, temp=None, wind=None, top=2):
    now, best, hits, have, pool = match(gid, side, temp, wind, top)
    n_now = sum(pd.notna(now[a[1]]) for a in ATTRS)
    same = pool[(pool.slot == now.slot) & (pool.off_home == now.off_home) & ((pool.week - now.week).abs() <= 2)]
    same = same.sort_values(["n_match", "n_have"], ascending=False).head(top)
    L = [f"# {now.offense} offense vs {now.defense} defense ({gid})",
         f"Attributes tonight: {n_now} of {len(ATTRS)} have data. Each is checked on its own tolerance "
         f"(Madden ratings within {MT}, production grades within {PT}, ages within 2-3 years, setting as listed). "
         "Games are ranked by how many attributes match. Nothing is averaged into one score.",
         f"Tonight's setting: {'home' if now.off_home == 1 else 'away'}, {now.slot}, week {now.week}, "
         f"{now.temp_f:.0f}F, wind {now.wind_f:.0f}, offense rest {now.off_rest} days, defense rest {now.def_rest} days.", "",
         "## Tonight's players: Madden card by edition (a season's card is set from the year before; the latest is the in-season update)"]
    L += trend(gid, side)
    L += ["", "Ratings used for a past game are game-time: that season's launch card moved toward the next edition's card by the week of the game.", ""]
    blocks = [("Closest on everything", best), (f"Closest with the same setting ({now.slot}, {'home' if now.off_home == 1 else 'away'}, week {now.week - 2}-{now.week + 2})", same)]
    for title, df in blocks:
        L.append(f"# {title}")
        for i, (_, row) in enumerate(df.iterrows(), 1):
            L.append(f"## {row.season} week {row.week}: {row.offense} {row.off_points:.0f}, {row.defense} {row.def_points:.0f} "
                     f"({'home' if row.off_home == 1 else 'away'}, {row.slot}) -- matches {row.n_match} of {row.n_have} attributes that game has data for")
            L.append(f"Offense: QB {row.QB1_name}, RB {row.RB1_name}, WR {row.WR1_name} / {row.WR2_name} / {row.WR3_name}, TE {row.TE1_name}, LT {row.OT1_name}")
            L.append(f"Defense: EDGE {row.dEDGE1_name}, DL {row.dDL1_name}, LB {row.dLB1_name}, CB {row.dCB1_name}, S {row.dS1_name}")
            L.append("")
            L.append("Stats from that game:")
            L += ["- " + s for s in box(row.game_id, row.offense)]
            L.append("")
            ex = explain(now, row, hits, have)
            miss = [e for e in ex if e[3] == "no"]
            L.append(f"Did NOT match ({len(miss)}), and what each could change tonight:")
            L += [f"- {e[0]}: {e[4]}" for e in miss]
            L.append("")
            L.append("<details><summary>Every attribute</summary>")
            L.append("")
            L.append("| Attribute | Tonight | That game | Match |")
            L.append("|---|---|---|---|")
            L += ["| " + " | ".join(e[:4]) + " |" for e in ex]
            L.append("")
            L.append("</details>")
            L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("gid", nargs="?")
    ap.add_argument("side", nargs="?")
    ap.add_argument("--temp", type=float)
    ap.add_argument("--wind", type=float)
    ap.add_argument("--top", type=int, default=2)
    a = ap.parse_args()
    if a.cmd == "build":
        build()
    else:
        out = report(a.gid, a.side, a.temp, a.wind, a.top)
        os.makedirs(os.path.join(ROOT, "results/trait_match"), exist_ok=True)
        f = os.path.join(ROOT, f"results/trait_match/{a.gid}_{a.side}.md")
        open(f, "w").write(out)
        print(out)
