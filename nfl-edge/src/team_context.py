"""Team context per game from play-by-play: defense judged with its own offense and score
state, the run game with its line, fullback use, and special teams.

Game-level table (one row per game and team) -> data/processed/team_context.parquet
season_so_far() gives each team's numbers from its EARLIER games that season (before the game).
"""
import os, glob
import numpy as np, pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "data/processed/team_context.parquet")
COLS = ["game_id", "posteam", "defteam", "play_type", "pass", "rush", "sack", "qb_dropback", "yards_gained",
        "score_differential", "punt_attempt", "field_goal_attempt", "field_goal_result", "kick_distance",
        "extra_point_result", "return_yards", "kickoff_attempt", "fixed_drive", "fixed_drive_result",
        "drive_play_count", "yardline_100", "run_location", "success", "qb_kneel", "posteam_score_post", "defteam_score_post",
        "complete_pass", "pass_attempt", "pass_touchdown", "interception", "air_yards", "fumble_lost", "penalty",
        "penalty_team", "fourth_down_converted", "fourth_down_failed", "half_seconds_remaining", "drive_inside20",
        "sack", "touchdown", "td_team", "receiving_player_id"]
COLS = list(dict.fromkeys(c for c in COLS if c != "receiving_player_id"))


def _rate(num, den):
    return num / den.replace(0, np.nan)


def game_table(d):
    d = d[d.posteam.notna()].copy()
    k = ["game_id", "posteam"]
    real = d[d.play_type.isin(["run", "pass"]) & (d.qb_kneel != 1)]
    out = pd.DataFrame(index=d.groupby(k).size().index)
    # ---- drives: punts, three-and-outs, starting field position
    dr = d.drop_duplicates(["game_id", "posteam", "fixed_drive"])
    out["drives"] = dr.groupby(k).size()
    out["punts"] = d[d.punt_attempt == 1].groupby(k).size()
    out["three_outs"] = dr[(dr.fixed_drive_result == "Punt") & (dr.drive_play_count <= 4)].groupby(k).size()
    out["start_yds"] = (100 - dr.yardline_100).groupby([dr.game_id, dr.posteam]).mean()
    out["points"] = d.groupby(k).posteam_score_post.max()
    # ---- run game with the line
    ru = real[real.rush == 1]
    out["run_in_succ"] = ru[ru.run_location == "middle"].groupby(k).success.mean()
    out["run_out_succ"] = ru[ru.run_location.isin(["left", "right"])].groupby(k).success.mean()
    out["stuffed"] = _rate(ru[ru.yards_gained <= 0].groupby(k).size(), ru.groupby(k).size())
    out["ypc"] = ru.groupby(k).yards_gained.mean()
    # ---- special teams (as kicking team)
    fg = d[d.field_goal_attempt == 1]
    out["fg_att"] = fg.groupby(k).size()
    out["fg_made"] = fg[fg.field_goal_result == "made"].groupby(k).size()
    fg40 = fg[fg.kick_distance >= 40]
    out["fg40_att"] = fg40.groupby(k).size()
    out["fg40_made"] = fg40[fg40.field_goal_result == "made"].groupby(k).size()
    pu = d[d.punt_attempt == 1]
    out["punt_net"] = (pu.kick_distance - pu.return_yards.fillna(0)).groupby([pu.game_id, pu.posteam]).mean()
    out["punt_ret_allowed"] = pu.groupby(k).return_yards.mean()
    ko = d[d.kickoff_attempt == 1]  # posteam = receiving team on kickoffs
    out["kr_avg"] = ko.groupby(k).return_yards.mean()
    out = out.reset_index().rename(columns={"posteam": "team"})
    # returns made BY this team on punts (punting team is posteam, returner is defteam)
    pr = pu.groupby(["game_id", "defteam"]).return_yards.mean().rename("pr_avg").reset_index().rename(columns={"defteam": "team"})
    kc = ko.groupby(["game_id", "defteam"]).return_yards.mean().rename("kr_cov_allowed").reset_index().rename(columns={"defteam": "team"})
    out = out.merge(pr, on=["game_id", "team"], how="left").merge(kc, on=["game_id", "team"], how="left")
    # ---- passing broken into its parts, explosives, turnovers, red zone, 4th down, 2-minute, penalties
    def unit(frame, key, pre):
        pa = frame[(frame.pass_attempt == 1) & (frame.sack != 1)]
        g = pa.groupby(key)
        r = pd.DataFrame({
            f"{pre}comp_rate": g.complete_pass.mean(),
            f"{pre}ypa": g.yards_gained.mean(),
            f"{pre}td_rate": g.pass_touchdown.mean(),
            f"{pre}int_rate": g.interception.mean(),
            f"{pre}adot": g.air_yards.mean(),
        })
        dbk = frame[frame.qb_dropback == 1].groupby(key)
        r[f"{pre}sack_rate"] = dbk.sack.mean()
        pl = frame[frame.play_type.isin(["run", "pass"])]
        r[f"{pre}explosive_pass"] = pl[(pl["pass"] == 1) & (pl.yards_gained >= 20)].groupby(key).size()
        r[f"{pre}explosive_run"] = pl[(pl.rush == 1) & (pl.yards_gained >= 10)].groupby(key).size()
        r[f"{pre}turnovers"] = frame.groupby(key).interception.sum() + frame.groupby(key).fumble_lost.sum()
        drv = frame.drop_duplicates(["game_id", key[1], "fixed_drive"])
        rz = drv[drv.drive_inside20 == 1]
        r[f"{pre}rz_td_rate"] = (rz.fixed_drive_result == "Touchdown").groupby([rz.game_id, rz[key[1]]]).mean()
        r[f"{pre}fourth_att"] = (frame.fourth_down_converted.fillna(0) + frame.fourth_down_failed.fillna(0)).groupby([frame.game_id, frame[key[1]]]).sum()
        r[f"{pre}fourth_conv"] = _rate(frame.groupby(key).fourth_down_converted.sum(), r[f"{pre}fourth_att"])
        two = frame[(frame.half_seconds_remaining <= 120) & frame.play_type.isin(["run", "pass"])]
        r[f"{pre}two_min_ypp"] = two.groupby(key).yards_gained.mean()
        r = r.reset_index().rename(columns={key[1]: "team"})
        for c in [f"{pre}explosive_pass", f"{pre}explosive_run", f"{pre}turnovers"]:
            r[c] = r[c].fillna(0)
        return r
    out = out.merge(unit(d, ["game_id", "posteam"], ""), on=["game_id", "team"], how="left")
    out = out.merge(unit(d, ["game_id", "defteam"], "a_"), on=["game_id", "team"], how="left")
    pen = d[d.penalty == 1].groupby(["game_id", "penalty_team"]).size().rename("penalties").reset_index().rename(columns={"penalty_team": "team"})
    out = out.merge(pen, on=["game_id", "team"], how="left")
    out["penalties"] = out.penalties.fillna(0)
    # ---- defense by score state (team = defteam; score_differential is from the offense's view)
    db = d[(d.qb_dropback == 1)]
    sd = d.score_differential
    def by_state(frame, col_fn, name):
        f = frame.copy()
        diff = f.score_differential
        f["state"] = np.where(diff <= -8, "ahead", np.where(diff >= 8, "behind", "close"))  # defense's view
        r = f.groupby(["game_id", "defteam", "state"]).apply(col_fn).unstack("state")
        r.columns = [f"{name}_{c}" for c in r.columns]
        return r.reset_index().rename(columns={"defteam": "team"})
    s1 = by_state(db, lambda x: x.sack.mean(), "def_sack")
    s2 = by_state(real, lambda x: x["pass"].mean(), "opp_pass_rate")
    s3 = by_state(real[real.rush == 1], lambda x: x.yards_gained.mean(), "def_ypc")
    s4 = by_state(real[real.rush == 1], lambda x: (x.yards_gained <= 0).mean(), "def_stuff")
    for s in (s1, s2, s3, s4):
        out = out.merge(s, on=["game_id", "team"], how="left")
    return out


def build():
    parts = []
    for f in sorted(glob.glob(os.path.join(ROOT, "data/raw/pbp/*.parquet"))):
        d = pd.read_parquet(f, columns=[c for c in COLS])
        parts.append(game_table(d))
    t = pd.concat(parts, ignore_index=True)
    # fullback touches
    pg = pd.read_parquet(os.path.join(ROOT, "data/processed/player_games.parquet"),
                         columns=["game_id", "team", "position", "carries", "targets"])
    fb = pg[pg.position == "FB"].fillna(0)
    fb = (fb.carries + fb.targets).groupby([fb.game_id, fb.team]).sum().rename("fb_touches").reset_index()
    t = t.merge(fb, on=["game_id", "team"], how="left")
    t["fb_touches"] = t.fb_touches.fillna(0)
    t = t.merge(pfr_table(), on=["game_id", "team"], how="left").merge(ftn_table(), on=["game_id", "team"], how="left")
    t["season"] = t.game_id.str[:4].astype(int)
    t["week"] = t.game_id.str[5:7].astype(int)
    t = t.drop_duplicates(["game_id", "team"])
    t.to_parquet(OUT, index=False)
    return t


def _read(k):
    fs = sorted(glob.glob(os.path.join(ROOT, f"data/raw/{k}/*.csv")))
    return pd.concat([pd.read_csv(f, low_memory=False) for f in fs], ignore_index=True) if fs else pd.DataFrame()


def pfr_table():
    """PFR advanced (2018+): broken tackles, yards before/after contact, missed tackles, pressure, blitz."""
    ru = _read("pfr_rush"); rc = _read("pfr_rec"); de = _read("pfr_def")
    k = ["game_id", "team"]
    a = ru.groupby(k).agg(carries_pfr=("carries", "sum"), ybc=("rushing_yards_before_contact", "sum"),
                          yac=("rushing_yards_after_contact", "sum"), rush_btk=("rushing_broken_tackles", "sum"))
    a["ybc_per_carry"] = a.ybc / a.carries_pfr.replace(0, np.nan)
    a["yac_per_carry"] = a.yac / a.carries_pfr.replace(0, np.nan)
    b = rc.groupby(k).agg(rec_btk=("receiving_broken_tackles", "sum"), drops=("receiving_drop", "sum"))
    c = de.groupby(k).agg(def_missed_tkl=("def_missed_tackles", "sum"), def_pressures=("def_pressures", "sum"),
                          def_blitzes=("def_times_blitzed", "sum"), def_hurries=("def_times_hurried", "sum"))
    out = a[["ybc_per_carry", "yac_per_carry", "rush_btk"]].join(b, how="outer").join(c, how="outer").reset_index()
    return out


def ftn_table():
    """FTN charting (2022+): scheme tendencies per offense and defense."""
    f = _read("ftn")
    if f.empty:
        return pd.DataFrame(columns=["game_id", "team"])
    pb = []
    for y in sorted(f.season.unique()):
        p = pd.read_parquet(os.path.join(ROOT, f"data/raw/pbp/{int(y)}.parquet"), columns=["game_id", "play_id", "posteam", "defteam", "play_type"])
        pb.append(p)
    pb = pd.concat(pb)
    f = f.merge(pb, left_on=["nflverse_game_id", "nflverse_play_id"], right_on=["game_id", "play_id"], how="inner")
    f = f[f.play_type.isin(["run", "pass"])]
    for c in ["is_play_action", "is_motion", "is_rpo", "is_screen_pass", "is_no_huddle"]:
        f[c] = f[c].astype(str).str.lower().isin(["true", "1", "1.0"]).astype(float)
    f["blitz"] = (pd.to_numeric(f.n_blitzers, errors="coerce") > 0).astype(float)
    o = f.groupby(["game_id", "posteam"]).agg(play_action=("is_play_action", "mean"), motion=("is_motion", "mean"),
                                              rpo=("is_rpo", "mean"), screens=("is_screen_pass", "mean"),
                                              no_huddle=("is_no_huddle", "mean"), box_faced=("n_defense_box", "mean")).reset_index().rename(columns={"posteam": "team"})
    d = f.groupby(["game_id", "defteam"]).agg(def_blitz_rate=("blitz", "mean"), def_rushers=("n_pass_rushers", "mean"),
                                              def_box=("n_defense_box", "mean")).reset_index().rename(columns={"defteam": "team"})
    return o.merge(d, on=["game_id", "team"], how="outer")


PARTS = ["comp_rate", "ypa", "td_rate", "int_rate", "adot", "sack_rate", "explosive_pass", "explosive_run",
         "turnovers", "rz_td_rate", "fourth_att", "fourth_conv", "two_min_ypp"]
STATS = PARTS + ["a_" + x for x in PARTS] + ["penalties", "ybc_per_carry", "yac_per_carry", "rush_btk", "rec_btk", "drops", "def_missed_tkl", "def_pressures",
         "def_blitzes", "def_hurries", "play_action", "motion", "rpo", "screens", "no_huddle", "box_faced",
         "def_blitz_rate", "def_rushers", "def_box",
"points", "punts", "three_outs", "start_yds", "run_in_succ", "run_out_succ", "stuffed", "ypc",
         "fg_pct", "fg40_pct", "punt_net", "punt_ret_allowed", "kr_avg", "pr_avg", "kr_cov_allowed",
         "def_sack_ahead", "def_sack_close", "def_sack_behind", "opp_pass_rate_ahead", "opp_pass_rate_close",
         "opp_pass_rate_behind", "def_ypc_close", "def_ypc_ahead", "def_stuff_close", "fb_touches"]


def season_so_far(t=None):
    t = pd.read_parquet(OUT) if t is None else t
    t = t.sort_values(["season", "week"]).copy()
    # rates over the season so far use made / attempted sums (not an average of game rates)
    g = t.groupby(["season", "team"])
    cum = lambda c: g[c].transform(lambda s: s.fillna(0).shift(1).cumsum())
    t["fg_pct"] = cum("fg_made") / cum("fg_att").replace(0, np.nan)
    t["fg40_pct"] = cum("fg40_made") / cum("fg40_att").replace(0, np.nan)
    for c in STATS:
        if c in ("fg_pct", "fg40_pct"):
            continue
        t[c] = g[c].transform(lambda s: s.shift(1).expanding().mean())
    return t[["game_id", "team", "season", "week"] + STATS]


if __name__ == "__main__":
    t = build()
    print(t.shape)
    print(t[t.game_id.str.startswith("2026_10")].head(4).T.head(40))
