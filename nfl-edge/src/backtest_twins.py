"""Walk-forward test of whole-game twins on games already played.

For each game, find its 20 closest past twins (only games before it), then
record how many of those twins the home side won and covered. Each game's
row is kept, so any threshold can be studied later. Nothing about the
target game's own result is used to find its twins.
"""
import os, sys
import numpy as np
import pandas as pd
from twins import load, whole_game, ROOT

def main(first=2022):
    c = load()
    games = c[(c.season >= first) & c.off_points.notna() & (c.game_type == "REG") & (c.off_home == 1)]
    games = games.sort_values("gd").drop_duplicates("game_id")
    rows = []
    for i, gid in enumerate(games.game_id):
        tg = c[c.game_id == gid]
        gd = tg.gd.iloc[0]
        pool = c[(c.gd < gd) & c.off_points.notna()]
        home, away, top, pa = whole_game(tg, pool)
        h = home
        rows.append({
            "game_id": gid, "season": h.season, "week": h.week, "home": h.offense, "away": away.offense,
            "line_home": h.line, "home_margin": h.result_margin, "home_vs_line": h.result_vs_line,
            "twins": len(top), "twin_similarity_top": round(100 * (1 - top._d.min()), 1),
            "twins_home_won": int((top.off_points > top._ap).sum()),
            "twins_home_covered": int((top.result_vs_line > 0).sum()),
            "twins_home_failed_cover": int((top.result_vs_line < 0).sum()),
            "home_moneyline": None,
        })
        if i % 100 == 0:
            print(i, gid, file=sys.stderr)
    r = pd.DataFrame(rows)
    out = os.path.join(ROOT, "results", "backtest_twins.csv")
    r.to_csv(out, index=False)
    print(out)

if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2022)
