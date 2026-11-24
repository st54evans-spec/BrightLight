"""Time of possession and what drives it, per team per game, from play-by-play.

Per game and team (as the offense):
  top_min        time of possession, minutes (sum of its drives)
  plays          offensive plays (runs + passes, incl. sacks/scrambles)
  drives         drives
  plays_per_drive
  sec_per_play   pace: possession seconds per play
  third_conv / third_att
  run_rate       share of plays that were designed runs
Writes data/processed/possession.parquet.
Also gives each team's season-so-far numbers BEFORE each game (offense and what its
defense allowed), used as matching attributes.
"""
import os, glob
import numpy as np, pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "data/processed/possession.parquet")


def _sec(s):
    try:
        m, x = str(s).split(":")
        return int(m) * 60 + int(x)
    except Exception:
        return np.nan


def build():
    rows = []
    for f in sorted(glob.glob(os.path.join(ROOT, "data/raw/pbp/*.parquet"))):
        cols = ["game_id", "posteam", "defteam", "fixed_drive", "drive_time_of_possession", "play_type",
                "down", "third_down_converted", "third_down_failed", "rush", "pass", "qb_kneel", "qb_spike"]
        d = pd.read_parquet(f, columns=cols)
        d = d[d.posteam.notna()]
        dr = d.drop_duplicates(["game_id", "posteam", "fixed_drive"])
        dr = dr.assign(sec=dr.drive_time_of_possession.map(_sec))
        top = dr.groupby(["game_id", "posteam"]).agg(top_sec=("sec", "sum"), drives=("fixed_drive", "nunique"))
        p = d[(d.play_type.isin(["run", "pass"])) & (d.qb_kneel != 1) & (d.qb_spike != 1)]
        g = p.groupby(["game_id", "posteam"]).agg(plays=("play_type", "size"), runs=("rush", "sum"),
                                                   third_conv=("third_down_converted", "sum"),
                                                   third_fail=("third_down_failed", "sum"))
        x = top.join(g, how="left").reset_index().rename(columns={"posteam": "team"})
        x = x.merge(d[["game_id", "posteam", "defteam"]].drop_duplicates(["game_id", "posteam"])
                    .rename(columns={"posteam": "team", "defteam": "opp"}), on=["game_id", "team"])
        rows.append(x)
    t = pd.concat(rows, ignore_index=True)
    t["top_min"] = t.top_sec / 60
    t["third_att"] = t.third_conv + t.third_fail
    t["third_rate"] = t.third_conv / t.third_att.replace(0, np.nan)
    t["plays_per_drive"] = t.plays / t.drives
    t["sec_per_play"] = t.top_sec / t.plays
    t["run_rate"] = t.runs / t.plays
    t["season"] = t.game_id.str[:4].astype(int)
    t["week"] = t.game_id.str[5:7].astype(int)
    t.to_parquet(OUT, index=False)
    return t


def season_so_far(t=None):
    """Each team's numbers from its earlier games that season (before the game), as offense
    and as defense (what opponents did against it)."""
    t = pd.read_parquet(OUT) if t is None else t
    t = t.sort_values(["season", "week"])
    f = ["top_min", "plays", "sec_per_play", "third_rate", "run_rate", "plays_per_drive"]
    off = t[["game_id", "season", "week", "team"] + f].copy()
    for c in f:
        off[f"o_{c}"] = off.groupby(["season", "team"])[c].transform(lambda s: s.shift(1).expanding().mean())
    de = t[["game_id", "season", "week", "opp"] + f].rename(columns={"opp": "team"}).sort_values(["season", "week"])
    for c in f:
        de[f"d_{c}"] = de.groupby(["season", "team"])[c].transform(lambda s: s.shift(1).expanding().mean())
    return (off[["game_id", "team"] + [f"o_{c}" for c in f]],
            de[["game_id", "team"] + [f"d_{c}" for c in f]])


if __name__ == "__main__":
    t = build()
    print(t.shape, t.season.min(), t.season.max())
    print(t[t.game_id.str.startswith("2026_10")][["game_id", "team", "top_min", "plays", "drives", "sec_per_play", "third_conv", "third_att", "run_rate"]].head(6).round(2))
    print("TOP sum per game check:", t.groupby("game_id").top_min.sum().describe().round(1).to_dict())
