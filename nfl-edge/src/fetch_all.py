"""Download every free nflverse player data set, season by season.

Sets and the seasons they cover:
  stats_player_week   1999+  every player's box score for every game (offense, defense, kicking)
  snap_counts         2012+  snaps per player per game (the only free source that lists linemen)
  pfr_advstats        2018+  pressures, blitzes, drops, bad throws, coverage targets/yards allowed,
                             broken tackles, yards before/after contact, missed tackles
  injuries            2009+  weekly injury report and practice status
  ftn_charting        2022+  per-play charting (play action, blitz, motion, etc.)
  players             all    birth date, position, height, weight, draft, rookie season
  pbp                 1999+  play by play (reduced to per-player situational splits elsewhere)
"""
import os, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
B = "https://github.com/nflverse/nflverse-data/releases/download"
LAST = 2026

JOBS = [("players", f"{B}/players/players.csv", "players.csv")]
for s in range(1999, LAST + 1):
    JOBS.append(("stats_player", f"{B}/stats_player/stats_player_week_{s}.csv", f"{s}.csv"))
    JOBS.append(("pbp", f"{B}/pbp/play_by_play_{s}.parquet", f"{s}.parquet"))
    if s >= 2012:
        JOBS.append(("snap_counts", f"{B}/snap_counts/snap_counts_{s}.csv", f"{s}.csv"))
    if s >= 2009:
        JOBS.append(("injuries", f"{B}/injuries/injuries_{s}.csv", f"{s}.csv"))
    if s >= 2018:
        for k in ["def", "pass", "rush", "rec"]:
            JOBS.append((f"pfr_{k}", f"{B}/pfr_advstats/advstats_week_{k}_{s}.csv", f"{s}.csv"))
    if s >= 2022:
        JOBS.append(("ftn", f"{B}/ftn_charting/ftn_charting_{s}.csv", f"{s}.csv"))


def get(job):
    folder, url, name = job
    d = os.path.join(RAW, folder)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name)
    if os.path.exists(path) and os.path.getsize(path) > 0 and "2026" not in name:
        return f"have {folder}/{name}"
    try:
        urllib.request.urlretrieve(url, path)
        return f"got {folder}/{name}"
    except Exception as e:
        if os.path.exists(path):
            os.remove(path)
        return f"MISSING {folder}/{name}: {e}"


if __name__ == "__main__":
    with ThreadPoolExecutor(8) as ex:
        for r in ex.map(get, JOBS):
            if "MISSING" in r:
                print(r, file=sys.stderr)
    print("done")
