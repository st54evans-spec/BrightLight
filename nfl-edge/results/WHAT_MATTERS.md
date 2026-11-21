# What matters against the line

Learned on 1311 games from 2018-2022, judged on 966 games from 2023-2026 that the learning never saw. "Against the line" = final margin minus the spread, so anything the betting market already priced counts for nothing here.

## One model using everything

Needed to profit at standard -110 odds: 52.4%.

| Model | Games | Side covered | Strongest 20% of picks | By season |
| --- | --- | --- | --- | --- |
| ridge | 917 | 51.7% | 54.9% (184 games) | 2023: 51%, 2024: 49%, 2025: 53%, 2026: 56% |
| boosted trees | 917 | 54.2% | 57.1% (184 games) | 2023: 57%, 2024: 54%, 2025: 52%, 2026: 53% |

## Grading points that held up in both periods (14 of 214)

Positive = higher for the offense's side goes with beating the spread. Correlations this small are normal against a betting line; anything above about 0.05 is notable.

| Grading point or pairing | 2018-2022 | 2023-2026 | With final margin |
| --- | --- | --- | --- |
| off_WR2_contested_win_rate | -0.106 | -0.032 | -0.110 |
| off_OT1_age | -0.068 | -0.031 | -0.020 |
| off_OT1_exp_years | -0.067 | -0.038 | -0.021 |
| off_OT2_exp_years | +0.063 | +0.069 | +0.095 |
| off_TE1_catch_rate | +0.061 | +0.040 | +0.116 |
| off_IOL3_exp_years | +0.061 | +0.083 | +0.062 |
| off_IOL1_exp_years | -0.060 | -0.056 | -0.045 |
| off_IOL3_age | +0.058 | +0.084 | +0.053 |
| off_OT2_age | +0.052 | +0.059 | +0.073 |
| off_IOL1_age | -0.049 | -0.052 | -0.037 |
| off_TE1_epa_per_target | +0.045 | +0.067 | +0.169 |
| def_DL1_pressure_rate | -0.041 | -0.052 | -0.092 |
| def_DL1_tackles | +0.033 | +0.064 | +0.032 |
| pair_TE1_epa_per_target_vs_S1_yards_per_target | +0.031 | +0.060 | +0.140 |

## Strongest with the final margin (what decides games, mostly already in the line)

| Grading point or pairing | With final margin |
| --- | --- |
| line | +0.437 |
| off_QB1_epa_per_dropback | +0.231 |
| off_QB1_clean_pocket_epa | +0.209 |
| off_QB1_road_epa | +0.199 |
| off_IOL2_unit_run_epa | +0.181 |
| off_QB1_primetime_epa | +0.177 |
| off_IOL1_unit_run_epa | +0.176 |
| off_OT1_unit_run_epa | +0.176 |
| off_TE1_epa_per_target | +0.169 |
| off_QB1_late_season_epa | +0.166 |
| off_QB1_third_down_epa | +0.165 |
| off_QB1_short_week_epa | +0.164 |
| off_QB1_accuracy_cpoe | +0.163 |
| off_QB1_ball_security | +0.157 |
| off_OT2_unit_run_epa | +0.156 |
| off_IOL3_unit_run_epa | +0.152 |
| off_OT2_unit_sacks_allowed | +0.146 |
| off_OT1_unit_sacks_allowed | +0.142 |
| pair_IOL1_unit_run_epa_vs_DL1_run_stop_tfl | +0.141 |
| pair_TE1_epa_per_target_vs_S1_yards_per_target | +0.140 |
| off_QB1_dome_epa | +0.139 |
| off_QB1_cold_epa | +0.137 |
| pair_WR2_epa_per_target_vs_CB2_yards_per_target | +0.137 |
| off_QB1_deep_epa | +0.134 |
| off_QB1_red_zone_epa | +0.130 |