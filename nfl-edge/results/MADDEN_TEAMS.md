# Team Madden numbers and every past game

EA's own team ratings for past editions are not published anywhere we can reach, so these team numbers come from each edition's player cards: each team's preseason roster ranked by overall at every spot (QB1, RB1, WR1-3, TE1, OL1-5, DL1-4, LB1-3, DB1-4, K, P). Every slot is kept, the unit numbers are those slots, offense and defense are the 11 starters each, team = all 24. One row per team per edition (data/processed/madden_teams.parquet). Every game with both teams' numbers: results/madden_team_games.csv.

Editions: Madden 02-26 launch rosters (2001-2025 seasons) and Madden 27 Week 8 update (2026). Madden 10 (2009 season) is missing in the source, so 2009 games have no numbers.

## Teams rated per edition

| Season | Teams | Best team (team number) | Worst |
| --- | --- | --- | --- |
| 2001 | 31 | BAL 83.1 | ATL 71.2 |
| 2002 | 32 | LAR 84.0 | HOU 70.8 |
| 2003 | 32 | TB 87.3 | ARI 77.7 |
| 2004 | 30 | TEN 88.0 | ARI 80.5 |
| 2005 | 32 | NE 88.4 | ARI 82.3 |
| 2006 | 32 | SEA 88.4 | NO 82.0 |
| 2007 | 32 | CHI 88.0 | HOU 80.5 |
| 2008 | 32 | DAL 89.8 | ATL 81.8 |
| 2010 | 32 | NYJ 84.5 | BUF 76.9 |
| 2011 | 32 | GB 84.2 | BUF 75.9 |
| 2012 | 32 | SF 86.4 | LAR 78.6 |
| 2013 | 32 | SF 89.2 | JAX 77.1 |
| 2014 | 32 | SF 86.8 | JAX 77.6 |
| 2015 | 32 | NE 84.9 | CHI 79.5 |
| 2016 | 32 | DAL 82.8 | CLE 75.9 |
| 2017 | 32 | NE 83.7 | NYJ 75.9 |
| 2018 | 32 | PHI 85.9 | NYG 76.8 |
| 2019 | 32 | PHI 82.8 | MIA 72.9 |
| 2020 | 32 | NO 83.5 | MIA 74.9 |
| 2021 | 32 | TB 83.4 | HOU 75.0 |
| 2022 | 32 | TB 81.5 | CHI 73.7 |
| 2023 | 32 | SF 82.0 | LAR 74.2 |
| 2024 | 32 | BAL 83.5 | LAC 74.9 |
| 2025 | 32 | BAL 83.1 | JAX 76.0 |
| 2026 | 32 | LAR 84.6 | MIA 76.6 |

## 1. Did the higher-rated Madden team win? (6446 games, 2001-2025)

Gap = team number difference.

| Gap | Games | Higher-rated team won |
| --- | --- | --- |
| 0-1 | 1777 | 51.7% |
| 1-2 | 1523 | 55.7% |
| 2-3 | 1224 | 60.0% |
| 3-4 | 900 | 63.1% |
| 4-6 | 780 | 68.7% |
| 6-+ | 242 | 68.6% |
| All | 6446 | 58.5% |

## 2. Did the higher-rated Madden team cover the spread? (6276 games)

Split by whether the betting market also favored that team. Needed to profit at -110: 52.4%.

| Gap | Market agrees: games | covered | Market disagrees (Madden's team is the underdog): games | covered |
| --- | --- | --- | --- | --- |
| 0-1 | 928 | 47.2% | 806 | 50.9% |
| 1-2 | 932 | 49.1% | 544 | 50.7% |
| 2-3 | 855 | 48.4% | 336 | 51.8% |
| 3-4 | 678 | 52.5% | 201 | 49.8% |
| 4-6 | 660 | 48.0% | 99 | 57.6% |
| 6-+ | 211 | 48.8% | 26 | 34.6% |
| All | 4264 | 48.9% | 2012 | 51.0% |

By season, Madden's team as the underdog:

| Season | Games | Covered |
| --- | --- | --- |
| 2001 | 84 | 48.8% |
| 2002 | 80 | 52.5% |
| 2003 | 82 | 52.4% |
| 2004 | 75 | 49.3% |
| 2005 | 92 | 40.2% |
| 2006 | 95 | 52.6% |
| 2007 | 83 | 45.8% |
| 2008 | 110 | 50.9% |
| 2010 | 73 | 46.6% |
| 2011 | 75 | 61.3% |
| 2012 | 91 | 46.2% |
| 2013 | 92 | 48.9% |
| 2014 | 85 | 54.1% |
| 2015 | 84 | 56.0% |
| 2016 | 82 | 61.0% |
| 2017 | 74 | 43.2% |
| 2018 | 92 | 48.9% |
| 2019 | 75 | 54.7% |
| 2020 | 79 | 60.8% |
| 2021 | 77 | 64.9% |
| 2022 | 69 | 58.0% |
| 2023 | 85 | 45.9% |
| 2024 | 99 | 40.4% |
| 2025 | 79 | 46.8% |

## 3. One model on all team numbers and unit duels (learned 2001-2015, judged 2016-2025)

| Model | Games | Covered | Strongest 20% | Picked winner | By season |
| --- | --- | --- | --- | --- | --- |
| Madden team numbers -> final margin (no line) | 2696 | 50.4% | 50.0% (540) | 59.5% | 2016: 52%, 2017: 49%, 2018: 52%, 2019: 51%, 2020: 49%, 2021: 53%, 2022: 52%, 2023: 48%, 2024: 48%, 2025: 50% |
| Madden team numbers + line -> margin vs the line | 2696 | 50.1% | 53.0% (540) | - | 2016: 49%, 2017: 50%, 2018: 50%, 2019: 47%, 2020: 46%, 2021: 50%, 2022: 52%, 2023: 56%, 2024: 51%, 2025: 49% |

## 4. Past games that look like each unplayed game

results/madden_team_twins/<game_id>.md: the 15 past games (2001-2025) whose home and away Madden teams are closest unit by unit (QB, RB, WR, TE, OL, DL, LB, DB for both sides), with how each one finished.