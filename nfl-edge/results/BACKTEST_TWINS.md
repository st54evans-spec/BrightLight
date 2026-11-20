# Game twins walk-forward test

Run on 2026-11-20 over 2,232 regular-season games from 2018 to 2026 week 11. For each game,
the 20 closest whole-game twins were found using only games played before it. Then we
checked what really happened. Per-game rows: [backtest_twins.csv](backtest_twins.csv).

## Picking winners: the twins see what the market sees

| Twins where the home team won | Games | Home team really won | Home team was favored |
| --- | --- | --- | --- |
| 0 to 6 of 20 | 114 | 37% | 19% |
| 7 to 9 | 485 | 42% | 37% |
| 10 to 11 | 579 | 52% | 59% |
| 12 to 14 | 772 | 58% | 72% |
| 15 to 20 | 282 | 73% | 91% |

The twins sort winners from losers, but the betting line already knew most of it.

## Against the spread: no edge yet

| Twins where the home team covered | Games | Home team really covered |
| --- | --- | --- |
| 0 to 5 of 20 | 82 | 54% |
| 6 to 7 | 323 | 51% |
| 8 to 9 | 697 | 49% |
| 10 | 368 | 48% |
| 11 to 12 | 551 | 44% |
| 13 to 14 | 179 | 52% |
| 15 to 20 | 32 | 32% |

Out of the box, twins don't beat the spread. When most twins say "home covers", the home
team covered a little less often, which may mean the market overrates what the twins see.
Season by season, betting the twins' side at 13+ or 7- covers ranged from 36% to 58%. No
stable edge.

## Leads (not proven, many cuts were looked at)

- Away underdogs where at most 8 of 20 twins had the home team winning: 97 games, the
  away side covered 56% and won outright 43%.
- Home underdogs where 12+ twins had the home team winning: 246 games, 50% covered. Nothing there.

## What this means for the next build step

Right now every grading point counts the same when matching. The next step is to learn
which grading points and pairings actually move results against the line (for example,
tackle vs edge rusher may matter far more than safety tackles), and to search for the
specific spots where twins and the line disagree most.
