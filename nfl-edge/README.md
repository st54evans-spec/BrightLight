# NFL edge research

Research code for the NFL player grading and game projection project.
Plan: see the "NFL Player Grading Plan" doc in the project.

## Run (in order)

```
pip install -r requirements.txt
python src/fetch_data.py        # games file + team passing by game
python src/fetch_all.py         # every free player data set, 1999 to now
python src/player_games.py      # one row per player per game, all sources joined
python src/grades.py            # position grading points, per game and going into each game
python src/matchups.py          # player-vs-player matchup cells for every game
python src/twins.py 2026_13_SF_NYG   # twins for one game (or --all-upcoming)
python src/backtest_twins.py 2018    # walk-forward test of twins vs the line
python src/dst_travel_test.py   # daylight saving travel test
```

## How it fits together

| Step | Output | What's in it |
| --- | --- | --- |
| Player-game store | `data/processed/player_games.parquet` | 579,667 player-games, 12,129 players, 7,423 games (1999 to now). Box score, snaps (2012+), pressures, coverage, drops, broken tackles (2018+), charting (2022+), situational splits from play by play, penalties, age, experience, injury status |
| Grades | `data/processed/player_grades.parquet` | For every player-game: `g_` what they did that game, `pre_` their 0-100 grade going in (earlier games only, recent weighted more), for every grading point of their position plus situational splits (cold, wind, dome, primetime, road, turf, late season, after clock change, short week) |
| Matchup cells | `data/processed/game_cells.parquet` | One row per offense per game: QB, RB, WR1-3, TE, OT1-2, IOL1-3 vs EDGE1-2, DL1-2, LB1-2, CB1-3, S1-2, each player's own grades, plus travel, body clock, rest, weather, roof, coaches, referee, line, and what happened |
| Twins | `results/twins/<game>.md` | For a game: each player pairing, the 15 closest past pass matchups, the 15 closest run matchups, and the 20 closest whole games, each listed on its own |

Grading points by position are defined in `src/grades.py` (`traits`). Data limits: linemen
have individual snap and penalty data only from 2012; coverage, pressure and broken-tackle
data start in 2018; charting (blitz, play action, drops, contested catches) in 2022.
Game results, scores, weather and lines go back to 1966 in `data/raw/history`.

Data comes from [nflverse](https://github.com/nflverse): game results, schedule,
stadium, weather and closing lines (`games.csv`), and play-by-play reduced to
per-team passing numbers per game. Raw data is not committed; the scripts rebuild it.

## Tests so far

- [Daylight saving travel test](results/DST_TRAVEL.md)
- Trip ledger: `python src/trip_ledger.py` writes every road game as its own row
  (route, time zones, body-clock kickoff, clock change, rest, trip before, weather,
  QBs, passing profiles, line, result) to `results/trip_ledger.csv`.
- Game matches: `python src/find_matches.py SF NYG 2026-12-06` lists every past trip
  that matches an upcoming game, layer by layer, one game per row. Examples in
  [results/matches](results/matches).
