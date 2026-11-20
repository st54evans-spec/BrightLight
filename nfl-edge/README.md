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
