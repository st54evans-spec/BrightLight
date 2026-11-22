"""Download free nflverse data and build small per-game team tables.

Raw play-by-play files are large, so each season is downloaded to a temp
folder, reduced to per-team-per-game passing numbers, and deleted.
"""
import os, sys, tempfile, urllib.request
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "data", "processed")
GAMES_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
PBP_URL = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{}.parquet"
COLS = ["game_id", "season", "week", "posteam", "defteam", "pass", "rush",
        "epa", "yards_gained", "sack", "interception", "pass_touchdown"]


def fetch_games():
    os.makedirs(RAW, exist_ok=True)
    path = os.path.join(RAW, "games.csv")
    urllib.request.urlretrieve(GAMES_URL, path)
    apply_overrides(path)


def apply_overrides(path):
    """The nflverse schedule can lag kickoff-time changes (it had JAX at NYG, week 11 2026, at 1 PM when
    it kicked at 4:25). schedule_overrides.csv holds corrections checked against a sportsbook."""
    ov = os.path.join(ROOT, "schedule_overrides.csv")
    if not os.path.exists(ov):
        return
    g = pd.read_csv(path)
    o = pd.read_csv(ov, dtype=str).set_index("game_id")
    hit = g.game_id.isin(o.index)
    g.loc[hit, "gametime"] = g.loc[hit, "game_id"].map(o.gametime)
    g.to_csv(path, index=False)


def fetch_pbp(first=1999, last=2026):
    os.makedirs(OUT, exist_ok=True)
    frames = []
    tmp = tempfile.mkdtemp()
    for season in range(first, last + 1):
        path = os.path.join(tmp, f"pbp_{season}.parquet")
        try:
            urllib.request.urlretrieve(PBP_URL.format(season), path)
        except Exception as e:  # season not published yet
            print(f"skip {season}: {e}", file=sys.stderr)
            continue
        df = pd.read_parquet(path, columns=COLS)
        os.remove(path)
        df = df[df.posteam.notna() & df.epa.notna()]
        p = df[df["pass"] == 1]
        g = p.groupby(["game_id", "season", "week", "posteam", "defteam"]).agg(
            pass_plays=("epa", "size"), pass_epa=("epa", "sum"),
            pass_yards=("yards_gained", "sum"), sacks=("sack", "sum"),
            ints=("interception", "sum"), pass_tds=("pass_touchdown", "sum"),
        ).reset_index()
        frames.append(g)
        print(f"{season}: {len(g)} team-games", file=sys.stderr)
    out = pd.concat(frames, ignore_index=True)
    out.to_csv(os.path.join(OUT, "team_game_pass.csv"), index=False)


if __name__ == "__main__":
    fetch_games()
    fetch_pbp()
