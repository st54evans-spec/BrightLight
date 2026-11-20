"""Matchup cells: one row per offense per game, every game.

Each row lines up the offense's players against the defense's players, role by
role, using the grades each player carried INTO the game:
  QB  vs the pass rush and coverage      WR1/WR2/WR3 vs CB1/CB2/CB3
  TE1 vs S1 and LB1                     each tackle vs each edge rusher, guards/center vs interior DL
  RB1 + OL run blocking vs DL/LB run defense
Roles come from who actually played (snaps from 2012, usage before). Every
player stays a separate column. The row also carries the game's context and
what actually happened, so past rows can be searched as twins.
"""
import os
import numpy as np
import pandas as pd
from trip_ledger import tz, REGION
from dst_travel_test import fall_back_sunday

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(ROOT, "data", "processed")

OFF = {
    "QB": (["QB"], 1, "qb_n", ["epa_per_dropback", "accuracy_cpoe", "deep_epa", "under_pressure_epa",
                                  "clean_pocket_epa", "third_down_epa", "red_zone_epa", "sack_avoidance",
                                  "ball_security", "rushing_epa", "cold_epa", "windy_epa", "dome_epa",
                                  "road_epa", "primetime_epa", "late_season_epa", "short_week_epa"]),
    "RB": (["RB"], 1, "carries", ["rush_epa", "rush_success", "third_down_rush_success", "red_zone_rush_epa",
                                    "explosive_runs", "yards_after_contact", "broken_tackles", "receiving_epa",
                                    "ball_security", "cold_epa", "road_epa"]),
    "WR": (["WR"], 3, "targets", ["epa_per_target", "catch_rate", "target_share", "deep_epa", "yac_per_catch",
                                    "third_down_epa", "red_zone_epa", "drop_rate", "contested_win_rate"]),
    "TE": (["TE"], 1, "targets", ["epa_per_target", "catch_rate", "target_share", "red_zone_epa", "snap_share"]),
    "OT": (["OL"], 2, "offense_snaps", ["holding_rate", "false_start_rate", "unit_pressure_allowed",
                                          "unit_sacks_allowed", "unit_run_epa"]),
    "IOL": (["OL"], 3, "offense_snaps", ["holding_rate", "false_start_rate", "unit_run_epa"]),
}
DEF = {
    "EDGE": (["EDGE"], 2, "defense_snaps", ["pressure_rate", "sack_rate", "qb_hit_rate", "third_down_rush",
                                              "run_stop_tfl", "missed_tackle_rate"]),
    "DL": (["DL"], 2, "defense_snaps", ["pressure_rate", "sack_rate", "run_stop_tfl", "tackles"]),
    "LB": (["LB"], 2, "defense_snaps", ["tackles", "run_stop_tfl", "missed_tackle_rate", "yards_per_target",
                                          "rating_allowed", "blitz_pressure"]),
    "CB": (["CB", "DB"], 3, "defense_snaps", ["yards_per_target", "rating_allowed", "completion_allowed",
                                                "ball_skills", "interceptions", "third_down_breakups", "pi_rate"]),
    "S": (["S"], 2, "defense_snaps", ["yards_per_target", "rating_allowed", "ball_skills", "tackles",
                                        "missed_tackle_rate", "run_stop_tfl"]),
}
ID_COLS = ["player_id", "player_display_name", "age", "exp_years"]


def pick(gr, pg_usage, groups, n, usage, extra_filter=None):
    d = gr[gr.group.isin(groups)]
    if extra_filter is not None:
        d = d[extra_filter(d)]
    u = d[usage].fillna(0) if usage in d else pd.Series(0, index=d.index)
    d = d.assign(_u=u).sort_values(["game_id", "team", "_u"], ascending=[True, True, False])
    d = d[d._u > 0] if usage != "defense_snaps" else d
    d["slot"] = d.groupby(["game_id", "team"]).cumcount() + 1
    return d[d.slot <= n]


def wide(d, role, traits):
    keep = ["game_id", "team", "slot"] + ID_COLS + [f"pre_{t}" for t in traits if f"pre_{t}" in d]
    w = d[keep].pivot_table(index=["game_id", "team"], columns="slot",
                            values=[c for c in keep if c not in ("game_id", "team", "slot")], aggfunc="first")
    w.columns = [f"{role}{int(s)}_{c.replace('pre_', '')}" for c, s in w.columns]
    return w


def build():
    gr = pd.read_parquet(os.path.join(PROC, "player_grades.parquet"))
    pg = pd.read_parquet(os.path.join(PROC, "player_games.parquet"),
                         columns=["game_id", "player_id", "attempts", "carries", "targets", "qb_n", "def_tackles_solo"])
    gr = gr.merge(pg.drop_duplicates(["game_id", "player_id"]), on=["game_id", "player_id"], how="left")
    pos = gr.position.astype(str)
    # Before 2012 there are no snap counts: rank defenders by their pre-game volume instead
    gr["defense_snaps"] = gr.defense_snaps.fillna(gr.get("vol_tackles", 0))
    off_parts, def_parts = [], []
    for role, (groups, n, usage, traits) in OFF.items():
        f = None
        if role == "OT":
            f = lambda d: d.position.isin(["T", "OT"])
        if role == "IOL":
            f = lambda d: d.position.isin(["G", "OG", "C"])
        off_parts.append(wide(pick(gr, pg, groups, n, usage, f), role, traits))
    for role, (groups, n, usage, traits) in DEF.items():
        def_parts.append(wide(pick(gr, pg, groups, n, usage), role, traits))
    off = pd.concat(off_parts, axis=1)
    de = pd.concat(def_parts, axis=1)
    off.columns = ["off_" + c for c in off.columns]
    de.columns = ["def_" + c for c in de.columns]

    g = pd.read_csv(os.path.join(ROOT, "data/raw/games.csv"))
    g = g[g.game_type.notna()]
    rows = []
    for side, op in [("home", "away"), ("away", "home")]:
        x = pd.DataFrame({
            "game_id": g.game_id, "season": g.season, "week": g.week, "game_type": g.game_type,
            "gameday": g.gameday, "weekday": g.weekday, "kickoff_ET": g.gametime,
            "offense": g[f"{side}_team"], "defense": g[f"{op}_team"],
            "off_home": (side == "home") & (g.location == "Home"), "neutral": g.location == "Neutral",
            "off_rest": g[f"{side}_rest"], "def_rest": g[f"{op}_rest"],
            "roof": g.roof, "surface": g.surface, "temp": g.temp, "wind": g.wind, "stadium": g.stadium,
            "div_game": g.div_game, "referee": g.referee,
            "off_coach": g[f"{side}_coach"], "def_coach": g[f"{op}_coach"],
            "line": np.where(side == "home", g.spread_line, -g.spread_line),
            "total_line": g.total_line,
            "off_points": g[f"{side}_score"], "def_points": g[f"{op}_score"],
        })
        rows.append(x)
    c = pd.concat(rows, ignore_index=True)
    c["gd"] = pd.to_datetime(c.gameday)
    c["days_after_clock_change"] = [(d.date() - fall_back_sunday(s)).days for d, s in zip(c.gd, c.season)]
    def zone(team, d, s):
        return tz(team, d.date(), s) if team in REGION else 0
    c["off_zones_travelled"] = [0 if h else zone(dn, d, s) - zone(o, d, s)
                                for o, dn, h, d, s in zip(c.offense, c.defense, c.off_home | c.neutral, c.gd, c.season)]
    c["def_zones_travelled"] = [0 if not h else zone(o, d, s) - zone(dn, d, s)
                                for o, dn, h, d, s in zip(c.offense, c.defense, c.off_home & ~c.neutral, c.gd, c.season)]
    kick_h = c.kickoff_ET.fillna("13:00").str[:2].astype(int)
    c["off_body_clock_hour"] = (kick_h + [zone(o, d, s) for o, d, s in zip(c.offense, c.gd, c.season)]) % 24
    c["def_body_clock_hour"] = (kick_h + [zone(o, d, s) for o, d, s in zip(c.defense, c.gd, c.season)]) % 24
    c["primetime"] = (c.kickoff_ET.fillna("13:00") >= "19:00") | c.weekday.isin(["Monday", "Thursday"])
    c = c.drop(columns="gd")
    # What actually happened for this offense (from play by play)
    tp = pd.read_csv(os.path.join(PROC, "team_game_pass.csv"))
    tp = tp.groupby(["game_id", "posteam"]).agg(pass_plays=("pass_plays", "sum"), pass_epa=("pass_epa", "sum"),
                                                sacks=("sacks", "sum"), ints=("ints", "sum"))
    tp["result_pass_epa_per_play"] = tp.pass_epa / tp.pass_plays
    tp["result_sack_rate"] = tp.sacks / tp.pass_plays
    rush = gr.groupby(["game_id", "team"]).agg(ru_epa=("g_rush_epa", "count"))
    c = c.join(tp[["result_pass_epa_per_play", "result_sack_rate", "ints"]].rename(columns={"ints": "result_ints"}),
               on=["game_id", "offense"])
    pgr = pd.read_parquet(os.path.join(PROC, "player_games.parquet"), columns=["game_id", "team", "ru_epa", "ru_n"])
    ru = pgr.groupby(["game_id", "team"]).sum()
    c = c.join((ru.ru_epa / ru.ru_n.replace(0, np.nan)).rename("result_rush_epa_per_play"), on=["game_id", "offense"])
    c["result_margin"] = c.off_points - c.def_points
    c["result_vs_line"] = c.result_margin - c.line
    c = c.join(off, on=["game_id", "offense"]).join(de, on=["game_id", "defense"])
    c.to_parquet(os.path.join(PROC, "game_cells.parquet"), index=False)
    print("cells", c.shape)


if __name__ == "__main__":
    build()
