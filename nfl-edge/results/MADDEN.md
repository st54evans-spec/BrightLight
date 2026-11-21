# Madden ratings

Every player's Madden card for every edition we could reach, each attribute kept on its own (data/processed/madden_ratings.parquet, one row per player per edition). Season = the NFL season the edition was played for (Madden 25 = 2024). Ratings are the launch cards for 2001-2025 and the Week 8 update for 2026.

## What we have

| Season | Madden | Players rated | Attributes rated |
| --- | --- | --- | --- |
| 2001 | 02 | 1226 | 21 |
| 2002 | 03 | 1298 | 1 |
| 2003 | 04 | 1352 | 22 |
| 2004 | 05 | 1243 | 8 |
| 2005 | 06 | 1350 | 21 |
| 2006 | 07 | 1321 | 39 |
| 2007 | 08 | 1372 | 47 |
| 2008 | 09 | 1384 | 48 |
| 2009 | 10 | 19 | 3 |
| 2010 | 11 | 1341 | 50 |
| 2011 | 12 | 1336 | 17 |
| 2012 | 13 | 1580 | 46 |
| 2013 | 14 | 1509 | 49 |
| 2014 | 15 | 1545 | 45 |
| 2015 | 16 | 1559 | 45 |
| 2016 | 17 | 1767 | 46 |
| 2017 | 18 | 1721 | 50 |
| 2018 | 19 | 1695 | 51 |
| 2019 | 20 | 1666 | 51 |
| 2020 | 21 | 1762 | 51 |
| 2021 | 22 | 1598 | 52 |
| 2022 | 23 | 1772 | 51 |
| 2023 | 24 | 1726 | 51 |
| 2024 | 25 | 1799 | 51 |
| 2025 | 26 | 2065 | 51 |
| 2026 | 27 | 1958 | 52 |

Gaps: Madden 03 (2002) sheet has only the overall rating; Madden 10 (2009) sheet is essentially empty in the source; Madden 05 and 12 sheets carry only part of the attributes. Nothing was filled in by guessing.

## How many of our lineup slots have a Madden card

| Season | Player slots | With Madden | Share |
| --- | --- | --- | --- |
| 1999 | 7548.0 | 0.0 | 0% |
| 2000 | 7604.0 | 0.0 | 0% |
| 2001 | 7506.0 | 6656.0 | 89% |
| 2002 | 7758.0 | 6761.0 | 87% |
| 2003 | 5992.0 | 5290.0 | 88% |
| 2004 | 6007.0 | 4831.0 | 80% |
| 2005 | 6088.0 | 5373.0 | 88% |
| 2006 | 6085.0 | 5169.0 | 85% |
| 2007 | 6025.0 | 5244.0 | 87% |
| 2008 | 6080.0 | 5280.0 | 87% |
| 2009 | 8031.0 | 161.0 | 2% |
| 2010 | 8039.0 | 6824.0 | 85% |
| 2011 | 8036.0 | 6057.0 | 75% |
| 2012 | 8019.0 | 7233.0 | 90% |
| 2013 | 10822.0 | 9678.0 | 89% |
| 2014 | 10787.0 | 9744.0 | 90% |
| 2015 | 10788.0 | 9646.0 | 89% |
| 2016 | 11023.0 | 9901.0 | 90% |
| 2017 | 11361.0 | 10102.0 | 89% |
| 2018 | 11331.0 | 9935.0 | 88% |
| 2019 | 11292.0 | 9452.0 | 84% |
| 2020 | 11627.0 | 9920.0 | 85% |
| 2021 | 12315.0 | 10152.0 | 82% |
| 2022 | 12270.0 | 10275.0 | 84% |
| 2023 | 12352.0 | 10402.0 | 84% |
| 2024 | 12300.0 | 10496.0 | 85% |
| 2025 | 12298.0 | 10656.0 | 87% |
| 2026 | 6450.0 | 6286.0 | 98% |

## Do the ratings help against the line?

Same boosted-tree model, trained 2018-2022. Needed to profit at -110: 52.4%.

| Features | 2023-2025 games | Covered | Strongest 20% | By season | 2026 covered | 2026 strongest 20% |
| --- | --- | --- | --- | --- | --- | --- |
| Our grades only (current model) | 780 | 54.5% | 57.1% (156) | 2023: 57.3%, 2024: 54.4%, 2025: 51.9% | 46.0% (137) | 64.3% (28) |
| Madden ratings only (+ setting) | 780 | 51.9% | 55.1% (156) | 2023: 49.8%, 2024: 54.4%, 2025: 51.5% | 51.8% (137) | 60.7% (28) |
| Madden duels only (+ setting) | 780 | 46.9% | 43.6% (156) | 2023: 46.2%, 2024: 45.6%, 2025: 48.9% | 48.9% (137) | 39.3% (28) |
| Our grades + Madden ratings | 780 | 52.6% | 61.5% (156) | 2023: 55.7%, 2024: 53.2%, 2025: 48.9% | 54.7% (137) | 60.7% (28) |

## Madden points that held up in both periods (30 of 230)

Positive = higher for the offense's side goes with beating the spread.

| Rating or duel | 2018-2022 | 2023-2025 | With final margin |
| --- | --- | --- | --- |
| off_OT2_m_awareness | +0.038 | +0.108 | +0.112 |
| off_IOL1_m_passblock | -0.031 | -0.089 | +0.027 |
| def_CB1_m_overall | +0.046 | +0.079 | -0.009 |
| off_IOL3_m_awareness | +0.059 | +0.074 | +0.102 |
| duel_WR2_shortrouterunning_vs_CB2_zonecoverage | +0.045 | +0.072 | +0.116 |
| def_CB1_m_jumping | +0.039 | +0.066 | +0.016 |
| off_IOL1_m_runblockfinesse | -0.032 | -0.065 | +0.028 |
| def_CB1_m_zonecoverage | +0.054 | +0.065 | +0.010 |
| def_CB1_m_press | +0.034 | +0.062 | -0.015 |
| duel_WR2_release_vs_CB2_press | +0.052 | +0.061 | +0.120 |
| def_S1_m_hitpower | +0.035 | +0.057 | +0.020 |
| def_CB1_m_mancoverage | +0.041 | +0.055 | -0.007 |
| def_CB1_m_playrecognition | +0.048 | +0.053 | +0.002 |
| off_IOL1_m_runblock | -0.031 | -0.052 | +0.022 |
| duel_WR2_catchintraffic_vs_CB2_playrecognition | +0.060 | +0.052 | +0.132 |
| off_OT2_m_runblockpower | +0.032 | +0.048 | +0.105 |
| def_LB2_m_hitpower | +0.055 | +0.047 | +0.037 |
| off_IOL3_m_overall | +0.049 | +0.046 | +0.084 |
| def_CB1_m_agility | +0.047 | +0.041 | +0.032 |
| duel_WR2_deeprouterunning_vs_CB2_mancoverage | +0.039 | +0.038 | +0.134 |
| def_CB2_m_playrecognition | -0.031 | -0.037 | -0.091 |
| duel_WR3_release_vs_CB3_press | +0.031 | +0.035 | +0.087 |
| def_EDGE1_m_strength | +0.030 | +0.034 | +0.012 |
| off_WR1_m_catching | +0.030 | +0.033 | +0.121 |
| off_IOL3_m_runblockfinesse | +0.047 | +0.033 | +0.087 |
| off_WR1_m_overall | +0.040 | +0.033 | +0.148 |
| off_IOL3_m_passblock | +0.056 | +0.032 | +0.066 |
| off_WR2_m_release | +0.044 | +0.032 | +0.087 |
| off_WR1_m_shortrouterunning | +0.040 | +0.031 | +0.142 |
| off_IOL3_m_runblock | +0.039 | +0.030 | +0.088 |

## Strongest with the final margin (who wins, mostly already in the line)

| Rating or duel | With final margin |
| --- | --- |
| off_QB1_m_overall | +0.184 |
| off_QB1_m_awareness | +0.159 |
| off_QB1_m_throwunderpressure | +0.158 |
| off_QB1_m_throwaccuracyshort | +0.156 |
| off_QB1_m_playaction | +0.154 |
| off_QB1_m_throwonrun | +0.153 |
| duel_QB1_awareness_vs_LB1_playrecognition | +0.150 |
| off_WR1_m_deeprouterunning | +0.149 |
| off_WR1_m_overall | +0.148 |
| off_QB1_m_throwaccuracymid | +0.146 |
| off_WR1_m_shortrouterunning | +0.142 |
| duel_QB1_throwaccuracydeep_vs_S1_zonecoverage | +0.135 |
| duel_WR2_deeprouterunning_vs_CB2_mancoverage | +0.134 |
| duel_WR2_catchintraffic_vs_CB2_playrecognition | +0.132 |
| off_QB1_m_throwaccuracydeep | +0.130 |
| off_WR1_m_release | +0.127 |
| off_WR1_m_catching | +0.121 |
| duel_WR2_release_vs_CB2_press | +0.120 |
| duel_WR1_release_vs_CB1_press | +0.116 |
| duel_WR2_shortrouterunning_vs_CB2_zonecoverage | +0.116 |