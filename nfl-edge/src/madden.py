"""Madden ratings for every player, every edition we can reach (Madden 02 to Madden 27).

Sources (public GitHub, since EA's ratings site and maddenratings.weebly.com are
blocked from here):
  * theedgepredictor/nfl-madden-data: Madden 02-26 (NFL seasons 2001-2025).
      processed/<season>.csv  - launch ratings already tied to nflverse player ids
      raw/<season>.csv        - the original sheets, which carry attributes the
                                processed files drop (block shedding, power moves,
                                finesse moves, break sack, throw under pressure...)
  * gahnjamjan/madden27-player-database: Madden 27 (2026 season). NOTE: this is the
      Week 8 ratings update, not launch, so for 2026 games before week 8 it knows a
      little of what happened. The backtest keeps 2026 apart for that reason.

Season = the NFL season the edition was played for (Madden 25 = 2024 season).
Nothing is averaged or merged across editions: one row per player per edition,
every attribute in its own column (m_<attribute>). An attribute an edition did
not rate stays empty.

Output: data/processed/madden_ratings.parquet
"""
import os, re, subprocess
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "madden")
PROC = os.path.join(ROOT, "data", "processed")
REPOS = {"edge": "https://github.com/theedgepredictor/nfl-madden-data.git",
         "m27": "https://github.com/gahnjamjan/madden27-player-database.git"}

# Every spelling seen across editions -> one name
SYN = {"ovr": "overall", "overallrating": "overall",
       "runblocking": "runblock", "passblocking": "passblock", "runblockstrength": "runblockpower",
       "passblockstrength": "passblockpower", "runblockfootwork": "runblockfinesse",
       "passblockfootwork": "passblockfinesse", "impactblock": "impactblocking",
       "leadblocking": "leadblock", "ballcarriervision": "bcvision",
       "throwaccuracymiddle": "throwaccuracymid", "throwonthrun": "throwonrun", "throwontherun": "throwonrun",
       "mediumrouterunning": "midrouterunning", "spectactularcatch": "spectacularcatch",
       "return": "kickreturn", "accleration": "acceleration", "stength": "strength",
       "finnessemoves": "finessemoves", "finesseemove": "finessemoves", "finessemove": "finessemoves",
       "powermove": "powermoves", "mancover": "mancoverage", "zonecover": "zonecoverage",
       "shortthrowaccuracy": "throwaccuracyshort", "shortaccuracy": "throwaccuracyshort", "throwaccshort": "throwaccuracyshort",
       "mediumthrowaccuracy": "throwaccuracymid", "throwaccuracymedium": "throwaccuracymid",
       "middleaccuracy": "throwaccuracymid", "throwaccmid": "throwaccuracymid",
       "deepthrowaccuracy": "throwaccuracydeep", "deepaccuracy": "throwaccuracydeep",
       "deepthrowaccruacy": "throwaccuracydeep", "throwaccdeep": "throwaccuracydeep",
       "catch": "catching", "shortrouteruning": "shortrouterunning", "shortrr": "shortrouterunning",
       "mediumrr": "midrouterunning", "deeprr": "deeprouterunning", "changeofdir": "changeofdirection",
       "speccatch": "spectacularcatch"}
NOT_RATINGS = {"team", "position", "firstname", "lastname", "fullname", "number", "jerseynumber", "jerseynum",
               "salary", "contract", "yearspro", "age", "height", "weight", "season", "birthdate", "college",
               "playerhandedness", "handedness", "totalsalary", "signingbonus", "archetype", "runningstyle",
               "playerportrait", "primarykey", "importance", "morale", "celebration", "name", "teamname", "jersey", "swagger", "birthday", "birthyear", "dratfpick",
               "unnamed20", "teamid", "portraitid", "experience", "", "blank", "playerid", "yearsleft"}
M27 = {"accel_rating": "acceleration", "agility_rating": "agility", "awareness_rating": "awareness",
       "bcv_rating": "bcvision", "block_shed_rating": "blockshedding", "break_sack_rating": "breaksack",
       "break_tackle_rating": "breaktackle", "carry_rating": "carrying", "catch_rating": "catching",
       "change_of_direction_rating": "changeofdirection", "cit_rating": "catchintraffic",
       "finesse_moves_rating": "finessemoves", "hit_power_rating": "hitpower", "impact_block_rating": "impactblocking",
       "injury_rating": "injury", "juke_move_rating": "jukemove", "jump_rating": "jumping",
       "kick_acc_rating": "kickaccuracy", "kick_power_rating": "kickpower", "kick_ret_rating": "kickreturn",
       "lead_block_rating": "leadblock", "man_cover_rating": "mancoverage",
       "pass_block_finesse_rating": "passblockfinesse", "pass_block_power_rating": "passblockpower",
       "pass_block_rating": "passblock", "play_action_rating": "playaction", "play_rec_rating": "playrecognition",
       "power_moves_rating": "powermoves", "press_rating": "press", "pursuit_rating": "pursuit",
       "release_rating": "release", "route_run_deep_rating": "deeprouterunning",
       "route_run_med_rating": "midrouterunning", "route_run_short_rating": "shortrouterunning",
       "run_block_finesse_rating": "runblockfinesse", "run_block_power_rating": "runblockpower",
       "run_block_rating": "runblock", "spec_catch_rating": "spectacularcatch", "speed_rating": "speed",
       "spin_move_rating": "spinmove", "stamina_rating": "stamina", "stiff_arm_rating": "stiffarm",
       "strength_rating": "strength", "tackle_rating": "tackle", "throw_acc_deep_rating": "throwaccuracydeep",
       "throw_acc_mid_rating": "throwaccuracymid", "throw_acc_short_rating": "throwaccuracyshort",
       "throw_on_run_rating": "throwonrun", "throw_power_rating": "throwpower",
       "throw_under_pressure_rating": "throwunderpressure", "tough_rating": "toughness", "truck_rating": "trucking",
       "zone_cover_rating": "zonecoverage", "overall": "overall"}


def fetch():
    os.makedirs(RAW, exist_ok=True)
    for k, url in REPOS.items():
        d = os.path.join(RAW, k)
        if not os.path.isdir(d):
            subprocess.run(["git", "clone", "-q", "--depth", "1", url, d], check=True)


def canon(c):
    c = re.sub(r"^stats/|/value$", "", str(c))
    c = re.sub(r"[^a-z0-9]", "", c.lower())
    c = re.sub(r"^plyr", "", c)
    return SYN.get(c, c)


def nm(s):
    s = s.fillna("").astype(str).str.lower().str.replace(r"\b(jr|sr|ii|iii|iv|v)\b\.?", "", regex=True)
    return s.str.replace(r"[^a-z]", "", regex=True)


def raw_edition(y):
    r = pd.read_csv(os.path.join(RAW, "edge", "data", "madden", "raw", f"{y}.csv"), low_memory=False)
    r = r[[c for c in r.columns if not str(c).endswith("/diff")]]
    r.columns = [canon(c) for c in r.columns]
    r = r.loc[:, ~r.columns.duplicated()]
    if "fullname" not in r:
        if "name" in r:
            r["fullname"] = r["name"]
        elif "firstname" in r and "lastname" in r:
            r["fullname"] = r.firstname.astype(str) + " " + r.lastname.astype(str)
        else:
            r["fullname"] = ""
    if "overall" not in r:
        r["overall"] = np.nan
    rat = [c for c in r.columns if c not in NOT_RATINGS and pd.api.types.is_numeric_dtype(r[c])]
    out = r[["fullname"] + rat].copy()
    out["_nm"] = nm(out.fullname)
    return out.drop(columns="fullname")


def editions_2001_2025():
    rows = []
    for y in range(2001, 2026):
        p = pd.read_csv(os.path.join(RAW, "edge", "data", "madden", "processed", f"{y}.csv"), low_memory=False)
        p = p[p.overallrating.notna()].copy()       # roster padding with no Madden card
        p.columns = [canon(c) for c in p.columns]
        p = p.rename(columns={"playerid": "player_id", "pfrid": "pfr_id", "maddenid": "madden_id",
                              "positiongroup": "position_group", "highposgroup": "high_pos_group"})
        p["_nm"] = nm(p.fullname)
        r = raw_edition(y)
        # Raw sheets carry attributes processed dropped: attach them by name + overall (exact) for that edition
        extra = [c for c in r.columns if c not in p.columns and c not in ("_nm", "overall")]
        if extra:
            r2 = r[["_nm", "overall"] + extra].drop_duplicates(["_nm", "overall"])
            p = p.merge(r2, on=["_nm", "overall"], how="left")
        p["madden_edition"] = y + 1
        p["ratings_timing"] = "launch"
        rows.append(p)
    return pd.concat(rows, ignore_index=True)


def edition_2026(players):
    m = pd.read_csv(os.path.join(RAW, "m27", "madden27_ratings.csv"))
    out = m.rename(columns=M27)[["full_name", "team_short", "position", "age", "archetype"] + sorted(set(M27.values()))]
    out = out.rename(columns={"full_name": "fullname"})
    out["season"] = 2026
    out["madden_edition"] = 2027
    out["ratings_timing"] = m.iteration.astype(str)
    out["_nm"] = nm(out.fullname)
    # Tie to nflverse ids: name match, use position/team to split shared names
    pl = players[players.gsis_id.notna()].copy()
    pl["_nm"] = nm(pl.display_name)
    pl = pl[pl.last_season.fillna(0) >= 2024] if "last_season" in pl else pl
    one = pl.drop_duplicates("_nm", keep=False)[["_nm", "gsis_id", "pfr_id"]]
    out = out.merge(one, on="_nm", how="left")
    dup = out.gsis_id.isna()
    if dup.any():
        two = pl[pl._nm.isin(out.loc[dup, "_nm"])][["_nm", "gsis_id", "pfr_id", "position"]]
        fix = out.loc[dup, ["_nm", "position"]].reset_index().merge(two, on=["_nm", "position"], how="inner")
        fix = fix.drop_duplicates("index", keep=False).set_index("index")
        out.loc[fix.index, "gsis_id"] = fix.gsis_id
        out.loc[fix.index, "pfr_id"] = fix.pfr_id
    out = out.rename(columns={"gsis_id": "player_id", "team_short": "team"})
    return out


def build():
    fetch()
    a = editions_2001_2025()
    players = pd.read_csv(os.path.join(ROOT, "data", "raw", "players", "players.csv"), low_memory=False)
    b = edition_2026(players)
    team_fix = {"49ers": "SF", "Bears": "CHI", "Bengals": "CIN", "Bills": "BUF", "Broncos": "DEN", "Browns": "CLE",
                "Buccaneers": "TB", "Cardinals": "ARI", "Chargers": "LAC", "Chiefs": "KC", "Colts": "IND",
                "Commanders": "WAS", "Cowboys": "DAL", "Dolphins": "MIA", "Eagles": "PHI", "Falcons": "ATL",
                "Giants": "NYG", "Jaguars": "JAX", "Jets": "NYJ", "Lions": "DET", "Packers": "GB", "Panthers": "CAR",
                "Patriots": "NE", "Raiders": "LV", "Rams": "LA", "Ravens": "BAL", "Saints": "NO", "Seahawks": "SEA",
                "Steelers": "PIT", "Texans": "HOU", "Titans": "TEN", "Vikings": "MIN"}
    b["team"] = b.team.map(team_fix).fillna(b.team)
    d = pd.concat([a, b], ignore_index=True, sort=False)
    ids = ["player_id", "pfr_id", "madden_id", "season", "madden_edition", "ratings_timing", "fullname", "team",
           "position", "position_group", "age", "yearspro", "archetype", "runningstyle"]
    ids = [c for c in ids if c in d]
    rat = [c for c in d.columns if c not in ids and c not in NOT_RATINGS and not c.startswith("_")
           and pd.api.types.is_numeric_dtype(d[c])
           and c not in ("jerseynumber", "height", "weight", "rookieseason", "draftyear", "draftround", "draftpick",
                         "forty", "bench", "vertical", "broadjump", "cone", "shuttle", "lastseasonav")]
    out = d[ids].copy()
    for c in ["player_id", "pfr_id", "madden_id", "ratings_timing", "fullname", "team", "position",
              "position_group", "archetype", "runningstyle"]:
        if c in out:
            out[c] = out[c].where(out[c].notna(), None).astype("string")
    for c in rat:
        out[f"m_{c}"] = pd.to_numeric(d[c], errors="coerce")
    out = out.sort_values(["season", "team", "position", "fullname"])
    out.to_parquet(os.path.join(PROC, "madden_ratings.parquet"), index=False)
    cov = out.groupby("season").agg(players=("fullname", "size"), with_id=("player_id", lambda s: s.notna().sum()),
                                    attributes_rated=("m_overall", lambda s: 0))
    for s, x in out.groupby("season"):
        cov.loc[s, "attributes_rated"] = sum(x[c].notna().mean() > 0.5 for c in out.columns if c.startswith("m_"))
    print(cov.to_string())
    print("rows", out.shape, "attributes", len(rat))
    return out


if __name__ == "__main__":
    build()
