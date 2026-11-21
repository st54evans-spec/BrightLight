"""Position-specific grading points for every player in every game.

For each grading point we keep two things per player-game:
  g_<point>    what the player did in that game (a rate)
  pre_<point>  their grade going INTO that game, 0-100, built only from earlier
               games (recent games count more), pulled toward average when the
               player has little volume. 50 = average at the position that season.
Traits are never averaged together. Situational splits (cold, wind, dome,
primetime, road, turf, late in the season, after the clock change, short week)
are their own grading points.
"""
import os
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(ROOT, "data", "processed")
DECAY = 0.93          # each older game counts 7% less (half weight after ~10 games)

GROUP = {"QB": "QB", "RB": "RB", "FB": "RB", "HB": "RB", "WR": "WR", "TE": "TE",
         "T": "OL", "OT": "OL", "G": "OL", "OG": "OL", "C": "OL", "OL": "OL",
         "DT": "DL", "NT": "DL", "DL": "DL", "DE": "EDGE", "OLB": "OLB", "LB": "LB", "ILB": "LB",
         "MLB": "LB", "CB": "CB", "DB": "DB", "S": "S", "SS": "S", "FS": "S", "SAF": "S",
         "K": "K", "P": "P", "LS": "LS"}


def col(d, c):
    return d[c].fillna(0) if c in d else pd.Series(0.0, index=d.index)


def context(pg):
    g = pd.read_csv(os.path.join(ROOT, "data/raw/games.csv"))
    hist = os.path.join(ROOT, "data/raw/history/spreadspoke_scores.csv")
    g["gameday"] = pd.to_datetime(g.gameday)
    if os.path.exists(hist):  # fill missing weather from the 1966+ history file
        h = pd.read_csv(hist)
        h["gameday"] = pd.to_datetime(h.schedule_date)
        h = h.groupby("gameday")[["weather_temperature", "weather_wind_mph"]].first()
        g["temp"] = g.temp.fillna(g.gameday.map(h.weather_temperature))
        g["wind"] = g.wind.fillna(g.gameday.map(h.weather_wind_mph))
    from dst_travel_test import fall_back_sunday
    fb = g.season.map(lambda s: pd.Timestamp(fall_back_sunday(s)))
    gi = g.set_index("game_id")
    c = pd.DataFrame(index=pg.index)
    gid = pg.game_id
    roof = gid.map(gi.roof)
    outdoor = roof.isin(["outdoors", "open"])
    c["dome"] = ~outdoor
    c["cold"] = outdoor & (gid.map(gi.temp) <= 40)
    c["windy"] = outdoor & (gid.map(gi.wind) >= 15)
    kick = gid.map(gi.gametime).fillna("13:00")
    wd = gid.map(gi.weekday)
    c["primetime"] = (kick >= "19:00") | wd.isin(["Monday", "Thursday"])
    c["road"] = pg.team == gid.map(gi.away_team)
    c["turf"] = ~gid.map(gi.surface).fillna("grass").str.strip().eq("grass")
    c["late_season"] = gid.map(gi.week) >= 13
    c["after_clock_change"] = (pg.gameday >= gid.map(dict(zip(g.game_id, fb)))) & ~c.late_season
    rest = np.where(c.road, gid.map(gi.away_rest), gid.map(gi.home_rest))
    c["short_week"] = pd.Series(rest, index=pg.index) <= 5
    return c


def traits(d):
    """(name, numerator, denominator, higher_is_better) per position group."""
    T = {}
    att = col(d, "attempts") + col(d, "sacks_suffered")
    T["QB"] = [
        ("epa_per_dropback", col(d, "qb_epa"), col(d, "qb_n"), True),
        ("success_rate", col(d, "qb_succ"), col(d, "qb_n"), True),
        ("accuracy_cpoe", col(d, "passing_cpoe") * col(d, "attempts"), col(d, "attempts"), True),
        ("deep_epa", col(d, "qb_deep_epa"), col(d, "qb_deep_n"), True),
        ("under_pressure_epa", col(d, "qb_hit_epa"), col(d, "qb_hit_n"), True),
        ("clean_pocket_epa", col(d, "qb_clean_epa"), col(d, "qb_clean_n"), True),
        ("third_down_epa", col(d, "qb_3rd_epa"), col(d, "qb_3rd_n"), True),
        ("red_zone_epa", col(d, "qb_rz_epa"), col(d, "qb_rz_n"), True),
        ("late_close_epa", col(d, "qb_late_epa"), col(d, "qb_late_n"), True),
        ("sack_avoidance", col(d, "sacks_suffered"), att, False),
        ("ball_security", col(d, "passing_interceptions") + col(d, "sack_fumbles_lost") + col(d, "rushing_fumbles_lost"), att + col(d, "carries"), False),
        ("rushing_epa", col(d, "rushing_epa"), col(d, "carries"), True),
        ("bad_throw_rate", col(d, "pfrpass_passing_bad_throws"), col(d, "attempts").where(col(d, "pfrpass_passing_bad_throws").notna() & d.get("pfrpass_passing_bad_throws").notna(), 0), False),
        ("pressure_rate_faced", col(d, "pfrpass_times_pressured"), att.where(d.get("pfrpass_times_pressured").notna(), 0), False),
        ("vs_blitz_epa", col(d, "qb_blitz_epa"), col(d, "qb_blitz_n"), True),
        ("play_action_epa", col(d, "qb_pa_epa"), col(d, "qb_pa_n"), True),
        ("out_of_pocket_epa", col(d, "qb_oop_epa"), col(d, "qb_oop_n"), True),
    ]
    touches = col(d, "carries") + col(d, "receptions")
    T["RB"] = [
        ("rush_epa", col(d, "ru_epa"), col(d, "ru_n"), True),
        ("rush_success", col(d, "ru_succ"), col(d, "ru_n"), True),
        ("third_down_rush_success", col(d, "ru_3rd_succ"), col(d, "ru_3rd_n"), True),
        ("red_zone_rush_epa", col(d, "ru_rz_epa"), col(d, "ru_rz_n"), True),
        ("explosive_runs", col(d, "rushing_20"), col(d, "carries"), True),
        ("yards_after_contact", col(d, "pfrrush_rushing_yards_after_contact"), col(d, "carries").where(d.get("pfrrush_rushing_yards_after_contact").notna(), 0), True),
        ("broken_tackles", col(d, "pfrrush_rushing_broken_tackles") + col(d, "pfrrec_receiving_broken_tackles"), touches.where(d.get("pfrrush_rushing_broken_tackles").notna(), 0), True),
        ("receiving_epa", col(d, "re_epa"), col(d, "re_n"), True),
        ("ball_security", col(d, "rushing_fumbles_lost") + col(d, "receiving_fumbles_lost"), touches, False),
        ("workload_share", col(d, "carries"), pd.Series(1.0, index=d.index), True),
    ]
    rec = [
        ("epa_per_target", col(d, "re_epa"), col(d, "re_n"), True),
        ("catch_rate", col(d, "receptions"), col(d, "targets"), True),
        ("target_share", col(d, "target_share"), pd.Series(1.0, index=d.index).where(col(d, "targets") > 0, 0), True),
        ("air_yards_share", col(d, "air_yards_share"), pd.Series(1.0, index=d.index).where(col(d, "targets") > 0, 0), True),
        ("yac_per_catch", col(d, "receiving_yards_after_catch"), col(d, "receptions"), True),
        ("deep_epa", col(d, "re_deep_epa"), col(d, "re_deep_n"), True),
        ("third_down_epa", col(d, "re_3rd_epa"), col(d, "re_3rd_n"), True),
        ("red_zone_epa", col(d, "re_rz_epa"), col(d, "re_rz_n"), True),
        ("drop_rate", col(d, "pfrrec_receiving_drop"), col(d, "targets").where(d.get("pfrrec_receiving_drop").notna(), 0), False),
        ("contested_win_rate", col(d, "re_contested_won"), col(d, "re_contested"), True),
        ("ball_security", col(d, "receiving_fumbles_lost"), col(d, "receptions"), False),
    ]
    T["WR"] = rec
    T["TE"] = rec + [("snap_share", col(d, "offense_pct"), (col(d, "offense_snaps") > 0).astype(float), True)]
    osn = col(d, "offense_snaps")
    T["OL"] = [
        ("snap_share", col(d, "offense_pct"), (osn > 0).astype(float), True),
        ("holding_rate", col(d, "pen_hold"), osn, False),
        ("false_start_rate", col(d, "pen_false_start"), osn, False),
        ("other_penalty_rate", col(d, "pen_other"), osn, False),
        ("unit_sacks_allowed", col(d, "unit_sacks"), col(d, "unit_dropbacks"), False),
        ("unit_pressure_allowed", col(d, "unit_pressures"), col(d, "unit_dropbacks_pfr"), False),
        ("unit_run_epa", col(d, "unit_run_epa"), col(d, "unit_runs"), True),
        ("unit_yards_before_contact", col(d, "unit_ybc"), col(d, "unit_runs_pfr"), True),
    ]
    dsn = col(d, "defense_snaps")
    per = dsn.where(dsn > 0, 60.0)  # before 2012 there are no snap counts: per game (~60 snaps)
    rush = [
        ("pressure_rate", col(d, "pfrdef_def_pressures"), dsn.where(d.get("pfrdef_def_pressures").notna(), 0), True),
        ("sack_rate", col(d, "def_sacks"), per, True),
        ("qb_hit_rate", col(d, "def_qb_hits"), per, True),
        ("third_down_rush", col(d, "d_sack_3rd") + col(d, "d_hit_3rd"), per, True),
        ("run_stop_tfl", col(d, "def_tackles_for_loss"), per, True),
        ("tackles", col(d, "def_tackles_solo") + col(d, "def_tackle_assists") * 0.5, per, True),
        ("missed_tackle_rate", col(d, "pfrdef_def_missed_tackles"), (col(d, "pfrdef_def_tackles_combined") + col(d, "pfrdef_def_missed_tackles")), False),
        ("penalty_rate", col(d, "pen_other") + col(d, "pen_hold"), per, False),
    ]
    T["DL"] = rush
    T["EDGE"] = rush
    cover = [
        ("targets_per_snap", col(d, "pfrdef_def_targets"), dsn.where(d.get("pfrdef_def_targets").notna(), 0), False),
        ("yards_per_target", col(d, "pfrdef_def_yards_allowed"), col(d, "pfrdef_def_targets"), False),
        ("completion_allowed", col(d, "pfrdef_def_completions_allowed"), col(d, "pfrdef_def_targets"), False),
        ("rating_allowed", col(d, "pfrdef_def_passer_rating_allowed") * col(d, "pfrdef_def_targets"), col(d, "pfrdef_def_targets"), False),
        ("tds_allowed", col(d, "pfrdef_def_receiving_td_allowed"), col(d, "pfrdef_def_targets"), False),
        ("ball_skills", col(d, "def_pass_defended") + col(d, "def_interceptions"), per, True),
        ("interceptions", col(d, "def_interceptions"), per, True),
        ("third_down_breakups", col(d, "d_pd_3rd") + col(d, "d_int_3rd"), per, True),
        ("missed_tackle_rate", col(d, "pfrdef_def_missed_tackles"), (col(d, "pfrdef_def_tackles_combined") + col(d, "pfrdef_def_missed_tackles")), False),
        ("tackles", col(d, "def_tackles_solo") + col(d, "def_tackle_assists") * 0.5, per, True),
        ("pi_rate", col(d, "pen_dpi"), per, False),
    ]
    T["CB"] = cover
    T["S"] = cover + [("run_stop_tfl", col(d, "def_tackles_for_loss"), per, True)]
    T["DB"] = cover
    T["LB"] = [
        ("tackles", col(d, "def_tackles_solo") + col(d, "def_tackle_assists") * 0.5, per, True),
        ("run_stop_tfl", col(d, "def_tackles_for_loss"), per, True),
        ("missed_tackle_rate", col(d, "pfrdef_def_missed_tackles"), (col(d, "pfrdef_def_tackles_combined") + col(d, "pfrdef_def_missed_tackles")), False),
        ("yards_per_target", col(d, "pfrdef_def_yards_allowed"), col(d, "pfrdef_def_targets"), False),
        ("rating_allowed", col(d, "pfrdef_def_passer_rating_allowed") * col(d, "pfrdef_def_targets"), col(d, "pfrdef_def_targets"), False),
        ("blitz_pressure", col(d, "pfrdef_def_pressures"), col(d, "pfrdef_def_times_blitzed"), True),
        ("sack_rate", col(d, "def_sacks"), per, True),
        ("ball_skills", col(d, "def_pass_defended") + col(d, "def_interceptions"), per, True),
    ]
    T["OLB"] = T["EDGE"] + [T["LB"][3], T["LB"][4]]
    T["K"] = [
        ("fg_pct", col(d, "fg_made"), col(d, "fg_att"), True),
        ("fg_40_plus", col(d, "fg_made_40_49") + col(d, "fg_made_50_59") + col(d, "fg_made_60_"),
         col(d, "fg_made_40_49") + col(d, "fg_made_50_59") + col(d, "fg_made_60_") + col(d, "fg_missed_40_49") + col(d, "fg_missed_50_59") + col(d, "fg_missed_60_"), True),
        ("fg_50_plus", col(d, "fg_made_50_59") + col(d, "fg_made_60_"), col(d, "fg_made_50_59") + col(d, "fg_made_60_") + col(d, "fg_missed_50_59") + col(d, "fg_missed_60_"), True),
        ("pat_pct", col(d, "pat_made"), col(d, "pat_att"), True),
    ]
    T["P"] = [
        ("net_per_punt", col(d, "pt_net_yards"), col(d, "pt_att"), True),
        ("inside_20_rate", col(d, "pt_inside_20"), col(d, "pt_att"), True),
        ("touchback_rate", col(d, "pt_touchback"), col(d, "pt_att"), False),
    ]
    return T


# Primary production stat per group, split by game situation
PRIMARY = {"QB": ("qb_epa", "qb_n"), "RB": ("ru_epa", "ru_n"), "WR": ("re_epa", "re_n"), "TE": ("re_epa", "re_n")}


def unit_stats(pg):
    """Team pass protection and run blocking per game, credited to each lineman who played."""
    tg = pd.read_csv(os.path.join(PROC, "team_game_pass.csv"))
    tg = tg.groupby(["game_id", "posteam"]).agg(unit_sacks=("sacks", "sum"), unit_dropbacks=("pass_plays", "sum"))
    qb = pg[pg.position == "QB"].groupby(["game_id", "team"]).agg(
        unit_pressures=("pfrpass_times_pressured", lambda s: s.sum(min_count=1)),
        unit_dropbacks_pfr=("attempts", "sum"))
    qb.loc[qb.unit_pressures.isna(), "unit_dropbacks_pfr"] = 0
    rb = pg.groupby(["game_id", "team"]).agg(
        unit_run_epa=("ru_epa", "sum"), unit_runs=("ru_n", "sum"),
        unit_ybc=("pfrrush_rushing_yards_before_contact", lambda s: s.sum(min_count=1)),
        unit_runs_pfr=("carries", "sum"))
    rb.loc[rb.unit_ybc.isna(), "unit_runs_pfr"] = 0
    u = qb.join(rb, how="outer")
    u = u.join(tg.rename_axis(["game_id", "team"]), how="left")
    return u


def rolling(df, num, den, k):
    """Pre-game decayed rate per player with shrinkage toward the position average."""
    order = df.index
    pid = df.player_id.values
    n, dn = num.values.astype(float), den.values.astype(float)
    pre_n = np.zeros(len(df)); pre_d = np.zeros(len(df))
    sn = sd = 0.0
    last = None
    for i in range(len(df)):
        if pid[i] != last:
            sn = sd = 0.0
            last = pid[i]
        pre_n[i], pre_d[i] = sn, sd
        sn = sn * DECAY + n[i]
        sd = sd * DECAY + dn[i]
    return pre_n, pre_d


def build():
    pg = pd.read_parquet(os.path.join(PROC, "player_games.parquet"))
    pg = pg[pg.season_type.notna()].copy()
    pg["group"] = pg.position.map(GROUP)
    # 3-4 outside linebackers who rush the passer are edge players
    rushers = pg[pg.group == "OLB"].groupby(["player_id", "season"]).agg(
        r=("def_sacks", "sum"), h=("def_qb_hits", "sum"), g=("game_id", "size"))
    edge = ((rushers.r + rushers.h) / rushers.g >= 0.3)
    key = list(zip(pg.player_id, pg.season))
    is_edge = pd.Series([edge.get(k, False) for k in key], index=pg.index)
    pg.loc[(pg.group == "OLB") & is_edge, "group"] = "EDGE"
    pg.loc[pg.group == "OLB", "group"] = "LB"
    pg = pg[pg.group.notna() & (pg.group != "LS")]
    u = unit_stats(pg)
    pg = pg.join(u, on=["game_id", "team"])
    ctx = context(pg)
    for c in ctx:
        pg[f"ctx_{c}"] = ctx[c]
    pg = pg.sort_values(["player_id", "gameday"]).reset_index(drop=True)
    out_cols = ["game_id", "player_id", "player_display_name", "team", "opponent_team", "season", "week",
                "season_type", "gameday", "position", "group", "age", "exp_years", "height", "weight",
                "draft_round", "offense_snaps", "offense_pct", "defense_snaps", "defense_pct",
                "report_status", "practice_status"] + [f"ctx_{c}" for c in ctx]
    result = [pg[out_cols]]
    for grp, sub in pg.groupby("group"):
        T = traits(sub)
        T = T.get(grp, [])
        if grp in PRIMARY:
            e, n = PRIMARY[grp]
            for c in ctx:
                m = sub[f"ctx_{c}"].fillna(False).astype(bool)
                T.append((f"{c}_epa", col(sub, e).where(m, 0), col(sub, n).where(m, 0), True))
                T.append((f"not_{c}_epa", col(sub, e).where(~m, 0), col(sub, n).where(~m, 0), True))
        cols = {}
        for name, num, den, hib in T:
            num, den = num.fillna(0), den.fillna(0)
            valid = den > 0
            cols[f"g_{name}"] = (num / den).where(valid)
            # Position-season average and typical volume, for shrinkage
            season_rate = (num.groupby(sub.season).sum() / den.groupby(sub.season).sum().replace(0, np.nan))
            prev_rate = sub.season.map(season_rate.shift(1).fillna(season_rate))
            k = max(den[valid].median() * 3, 1e-6) if valid.any() else 1.0
            pn, pd_ = rolling(sub, num, den, k)
            rate = (pn + prev_rate.values * k) / (pd_ + k)
            cols[f"rate_{name}"] = pd.Series(rate, index=sub.index)
            cols[f"vol_{name}"] = pd.Series(pd_, index=sub.index).round(1)
            # Percentile vs everyone at the position that season going into their games
            r = cols[f"rate_{name}"].where(pd_ > 0)
            pct = r.groupby(sub.season).rank(pct=True)
            if not hib:
                pct = 1 - pct + (1 / r.groupby(sub.season).transform("count"))
            cols[f"pre_{name}"] = (pct * 100).round(1)
        result.append(pd.DataFrame(cols, index=sub.index))
        print(grp, len(sub), len(T), "grading points")
    gr = pd.concat([result[0]] + [pd.concat(result[1:])], axis=1) if len(result) > 1 else result[0]
    gr = gr.loc[:, ~gr.columns.duplicated()]
    gr.to_parquet(os.path.join(PROC, "player_grades.parquet"), index=False)
    print("rows", len(gr), "cols", gr.shape[1])


if __name__ == "__main__":
    build()
