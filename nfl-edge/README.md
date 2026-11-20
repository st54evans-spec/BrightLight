# NFL edge research

Research code for the NFL player grading and game projection project.
Plan: see the "NFL Player Grading Plan" doc in the project.

## Run

```
pip install -r requirements.txt
python src/fetch_data.py        # downloads free nflverse data (1999 to now)
python src/dst_travel_test.py   # daylight saving travel test
```

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
