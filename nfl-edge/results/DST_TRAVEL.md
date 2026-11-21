# Daylight saving travel test

Run on 2026-11-20 with regular-season games 1999 to 2026 week 11 (7,000+ games).

## Setup

- **Clock-change week:** games from the fall-back Sunday through the next Saturday
  (last Sunday of October before 2007, first Sunday of November since).
- **Weak pass defense:** worst third of the league in pass EPA allowed per dropback, using only
  games before this one (blended with last season early in the year).
- **Strong pass offense:** best third in pass EPA per dropback, same method.
- **Heavy favorite:** favored by 6.5+ points.
- **Beat the line:** final margin compared with the closing spread. 50% is break-even before
  the book's margin; about 52.4% is needed to profit at standard -110 odds.
- **z-score:** how far from 50% the cover rate is, given the sample. Under about 2 is easily luck.

## Results

| Spot | Games | Won | Covered | Pts vs line | z | Moneyline ROI |
| --- | --- | --- | --- | --- | --- | --- |
| A1 Travelling, clock-change week | 383 | 43.1% | 49.9% | -0.15 | -0.05 | +0.3% |
| A2 Travelling, all other weeks | 6,660 | 43.8% | 51.3% | -0.03 | 2.01 | -2.5% |
| A3 Travelling, week before the change | 373 | 41.3% | 49.3% | -0.38 | -0.26 | -11.8% |
| B West to east, 2+ time zones, clock-change week | 56 | 39.3% | 40.7% | -4.30 | -1.36 | -34.7% |
| B West to east, 2+ time zones, other weeks | 776 | 42.0% | 50.0% | -0.64 | 0.00 | -1.6% |
| B East to west, 2+ time zones, clock-change week | 44 | 54.5% | 58.1% | +3.33 | 1.07 | +40.1% |
| B East to west, 2+ time zones, other weeks | 782 | 43.5% | 51.2% | +0.08 | 0.69 | -0.7% |
| C1 Weak pass D underdog travelling, clock-change week | 21 | 23.8% | 60.0% | +1.76 | 0.89 | -5.8% |
| C2 Weak pass D underdog at home, clock-change week | 11 | 45.5% | 63.6% | +3.50 | 0.90 | +135.7% |
| C3 Weak pass D underdog travelling, other weeks | 391 | 16.4% | 49.6% | -1.23 | -0.15 | -15.9% |
| C4 Weak pass D underdog at home, other weeks | 210 | 23.3% | 56.0% | +0.47 | 1.74 | -0.5% |
| C5 Weak pass D underdog travelling, 2 weeks after change | 40 | 22.5% | 56.4% | +0.44 | 0.80 | +13.1% |

Moneyline odds exist from 2006 on, so ROI uses fewer games. Full table:
[dst_travel_summary.csv](dst_travel_summary.csv). Every game in the C spot:
[dst_spot_games.csv](dst_spot_games.csv).

## What it says

1. **Travel alone in the clock-change week does nothing.** 49.9% cover over 383 games.
2. **Direction may matter.** Teams going 2+ time zones west covered 58% and won outright more
   than expected; teams going 2+ zones east covered 41%. It fits the body-clock idea, but at
   44 and 56 games neither is past luck yet (z of 1.1 and -1.4, and we ran 16 comparisons).
3. **Your spot leans the right way but is tiny.** Weak pass defenses getting 6.5+ points
   against strong passing teams covered 60% (travelling, 21 games) and 64% (home, 11 games)
   in the clock-change week, against about 50% to 56% in other weeks. In 2026 all three
   such games covered and Arizona won outright at Dallas. Two big upsets drive the
   moneyline number, so that ROI is not reliable.
4. **Something else showed up:** heavy underdogs with weak pass defenses at home covered
   56% in all other weeks (210 games, z 1.74). Bigger sample, worth its own test.

None of these are proven. They are leads for the next round, where we add the player-level
detail (which corners face which receivers, OL vs pass rush) that should separate real
spots from noise.
