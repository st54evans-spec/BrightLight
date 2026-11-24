"""Player-game store: one row per player per game, every player, every game.

Joins every free source onto the same (game_id, player) key and keeps the raw
counts. Grades are built from this in grades.py. Nothing is averaged here.
"""
import os, glob
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "data", "processed")

PBP_COLS = ["game_id", "play_id", "season", "week", "season_type", "posteam", "defteam", "play_type",
            "down", "ydstogo", "yardline_100", "qtr", "score_differential", "air_yards", "epa", "success",
            "cpoe", "qb_hit", "sack", "interception", "complete_pass", "shotgun", "qb_scramble",
            "passer_player_id", "rusher_player_id", "receiver_player_id",
            "pass_defense_1_player_id", "pass_defense_2_player_id", "interception_player_id",
            "sack_player_id", "half_sack_1_player_id", "half_sack_2_player_id",
            "qb_hit_1_player_id", "qb_hit_2_player_id", "tackle_for_loss_1_player_id",
            "penalty_player_id", "penalty_type", "penalty", "pass", "rush"]


def _agg(df, key, prefix, cond=None):
    d = df if cond is None else df[cond]
    g = d.groupby(["game_id", key]).agg(n=("epa", "size"), epa=("epa", "sum"), succ=("success", "sum"))
    g.columns = [f"{prefix}_{c}" for c in g.columns]
    return g.rename_axis(["game_id", "player_id"])


def pbp_splits(season):
    p = pd.read_parquet(f"{RAW}/pbp/{season}.parquet", columns=PBP_COLS)
    p = p[p.epa.notna()]
    p["third"] = p.down.isin([3, 4])
    p["rz"] = p.yardline_100 <= 20
    p["deep"] = p.air_yards >= 20
    p["late_close"] = (p.qtr >= 4) & (p.score_differential.abs() <= 8)
    # FTN charting adds blitz / play action / out of pocket from 2022
    ftn_path = f"{RAW}/ftn/{season}.csv"
    if os.path.exists(ftn_path):
        f = pd.read_csv(ftn_path, usecols=["nflverse_game_id", "nflverse_play_id", "n_blitzers",
                                           "is_play_action", "is_qb_out_of_pocket", "is_drop",
                                           "is_contested_ball", "is_catchable_ball"])
        f = f.rename(columns={"nflverse_game_id": "game_id", "nflverse_play_id": "play_id"})
        p = p.merge(f, on=["game_id", "play_id"], how="left")
        p["blitz"] = p.n_blitzers.fillna(0) > 0
    pas = p[p["pass"] == 1]
    run = p[(p["rush"] == 1) & (p.qb_scramble != 1)]
    parts = [
        _agg(pas, "passer_player_id", "qb"),
        _agg(pas, "passer_player_id", "qb_3rd", pas.third),
        _agg(pas, "passer_player_id", "qb_rz", pas.rz),
        _agg(pas, "passer_player_id", "qb_deep", pas.deep),
        _agg(pas, "passer_player_id", "qb_hit", (pas.qb_hit == 1) | (pas.sack == 1)),
        _agg(pas, "passer_player_id", "qb_clean", (pas.qb_hit != 1) & (pas.sack != 1)),
        _agg(pas, "passer_player_id", "qb_late", pas.late_close),
        _agg(run, "rusher_player_id", "ru"),
        _agg(run, "rusher_player_id", "ru_3rd", run.third),
        _agg(run, "rusher_player_id", "ru_rz", run.rz),
        _agg(pas, "receiver_player_id", "re"),
        _agg(pas, "receiver_player_id", "re_3rd", pas.third),
        _agg(pas, "receiver_player_id", "re_rz", pas.rz),
        _agg(pas, "receiver_player_id", "re_deep", pas.deep),
    ]
    if "blitz" in p:
        parts += [_agg(pas, "passer_player_id", "qb_blitz", pas.blitz),
                  _agg(pas, "passer_player_id", "qb_pa", pas.is_play_action == True),
                  _agg(pas, "passer_player_id", "qb_oop", pas.is_qb_out_of_pocket == True)]
        dr = pas[pas.is_drop == True].groupby(["game_id", "receiver_player_id"]).size().rename("re_drops")
        ct = pas[pas.is_contested_ball == True].groupby(["game_id", "receiver_player_id"]).agg(
            re_contested=("complete_pass", "size"), re_contested_won=("complete_pass", "sum"))
        parts += [dr.rename_axis(["game_id", "player_id"]).to_frame(), ct.rename_axis(["game_id", "player_id"])]
    # Defensive play credit from play by play (who made the play, and on which downs)
    dfp = []
    for col, name in [("pass_defense_1_player_id", "d_pd"), ("pass_defense_2_player_id", "d_pd"),
                      ("interception_player_id", "d_int"), ("sack_player_id", "d_sack"),
                      ("half_sack_1_player_id", "d_hsack"), ("half_sack_2_player_id", "d_hsack"),
                      ("qb_hit_1_player_id", "d_hit"), ("qb_hit_2_player_id", "d_hit"),
                      ("tackle_for_loss_1_player_id", "d_tfl")]:
        x = p[p[col].notna()][["game_id", col, "third"]].rename(columns={col: "player_id"})
        x["stat"] = name
        dfp.append(x)
    dfp = pd.concat(dfp)
    d_all = dfp.pivot_table(index=["game_id", "player_id"], columns="stat", aggfunc="size", fill_value=0)
    d_3rd = dfp[dfp.third].pivot_table(index=["game_id", "player_id"], columns="stat", aggfunc="size", fill_value=0)
    d_3rd.columns = [f"{c}_3rd" for c in d_3rd.columns]
    parts += [d_all, d_3rd]
    # Penalties charged to each player, by type
    pen = p[(p.penalty == 1) & p.penalty_player_id.notna()].copy()
    pen["ptype"] = pen.penalty_type.fillna("Other").map(
        lambda t: "pen_hold" if "Holding" in t else "pen_false_start" if "False Start" in t
        else "pen_dpi" if "Defensive Pass Interference" in t else "pen_other")
    parts.append(pen.pivot_table(index=["game_id", "penalty_player_id"], columns="ptype", aggfunc="size",
                                 fill_value=0).rename_axis(["game_id", "player_id"]))
    out = pd.concat(parts, axis=1).reset_index()
    return out


def build():
    os.makedirs(OUT, exist_ok=True)
    players = pd.read_csv(f"{RAW}/players/players.csv", low_memory=False)
    pfr_map = players.dropna(subset=["pfr_id"]).set_index("pfr_id").gsis_id.to_dict()
    seasons = sorted(int(os.path.basename(f)[:4]) for f in glob.glob(f"{RAW}/stats_player/*.csv"))
    frames = []
    for s in seasons:
        st = pd.read_csv(f"{RAW}/stats_player/{s}.csv", low_memory=False)
        st = st.drop(columns=[c for c in ["headshot_url", "fg_made_list", "fg_missed_list", "fg_blocked_list",
                                          "fg_made_distance", "fg_missed_distance", "fg_blocked_distance"]
                              if c in st])
        keys = ["game_id", "player_id"]
        # Snap counts list every player who played, including linemen with no box score
        sc_path = f"{RAW}/snap_counts/{s}.csv"
        if os.path.exists(sc_path):
            sc = pd.read_csv(sc_path)
            sc["player_id"] = sc.pfr_player_id.map(pfr_map)
            sc = sc.dropna(subset=["player_id"]).rename(columns={"position": "snap_position", "opponent": "snap_opp",
                                                                 "team": "snap_team"})
            sc = sc[keys + ["snap_position", "snap_team", "snap_opp", "offense_snaps", "offense_pct",
                            "defense_snaps", "defense_pct", "st_snaps", "st_pct"]].drop_duplicates(keys)
            st = st.merge(sc, on=keys, how="outer")
        for k in ["def", "pass", "rush", "rec"]:
            path = f"{RAW}/pfr_{k}/{s}.csv"
            if os.path.exists(path):
                a = pd.read_csv(path)
                a["player_id"] = a.pfr_player_id.map(pfr_map)
                a = a.dropna(subset=["player_id"]).drop(columns=["pfr_game_id", "season", "week", "game_type", "team",
                                                                 "opponent", "pfr_player_name", "pfr_player_id"])
                a = a.add_prefix(f"pfr{k}_").rename(columns={f"pfr{k}_game_id": "game_id", f"pfr{k}_player_id": "player_id"})
                st = st.merge(a.drop_duplicates(keys), on=keys, how="left")
        st = st.merge(pbp_splits(s), on=keys, how="left")
        st["season"] = s
        frames.append(st)
        print(s, len(st))
    pg = pd.concat(frames, ignore_index=True)
    # Fill team / opponent / position for snap-only rows (mostly linemen)
    pg["team"] = pg.team.fillna(pg.get("snap_team"))
    pg["opponent_team"] = pg.opponent_team.fillna(pg.get("snap_opp"))
    info = players.set_index("gsis_id")
    pg["position"] = pg.position.fillna(pg.player_id.map(info.position)).fillna(pg.get("snap_position"))
    pg["player_display_name"] = pg.player_display_name.fillna(pg.player_id.map(info.display_name))
    # Week / type from game_id when missing
    g = pd.read_csv(f"{RAW}/games.csv")
    gi = g.set_index("game_id")
    pg["week"] = pg.game_id.map(gi.week)
    pg["season_type"] = pg.game_id.map(gi.game_type)
    pg["gameday"] = pd.to_datetime(pg.game_id.map(gi.gameday))
    # Body and career context: age on game day, years in the league, size, draft
    bd = pd.to_datetime(pg.player_id.map(info.birth_date), errors="coerce")
    pg["age"] = ((pg.gameday - bd).dt.days / 365.25).round(2)
    pg["exp_years"] = pg.season - pg.player_id.map(info.rookie_season)
    for c in ["height", "weight", "draft_round", "draft_pick", "college_name"]:
        pg[c] = pg.player_id.map(info[c])
    # Injury report status that week (2009+)
    inj = pd.concat([pd.read_csv(f) for f in glob.glob(f"{RAW}/injuries/*.csv")], ignore_index=True)
    inj = inj.drop_duplicates(["season", "week", "gsis_id"], keep="last")
    pg = pg.merge(inj[["season", "week", "gsis_id", "report_status", "practice_status", "report_primary_injury"]]
                  .rename(columns={"gsis_id": "player_id"}), on=["season", "week", "player_id"], how="left")
    pg = pg.dropna(subset=["game_id", "player_id"])
    pg.to_parquet(f"{OUT}/player_games.parquet", index=False)
    print("player-games:", len(pg), "players:", pg.player_id.nunique(), "games:", pg.game_id.nunique())
    return pg


if __name__ == "__main__":
    build()
