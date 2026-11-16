# Model comparison summary

All numbers are produced by `pipeline/model_comparison.py` from `results/folds.csv` (10 walk-forward folds, test seasons 2016-17 to 2025-26). Log loss is the primary metric (lower is better). Differences under 0.002 log loss are treated as ties. `mean_diff` is model minus default logistic regression at the same window/weighting (negative = better); `wins` = folds where the model has lower log loss.

## Data notes and flags

Games dropped by the feature-building try/except, per season (total 0 of 25271 games; zero-filled rows, where a team had no prior games in the lookback, total 15):

| season | games | rows | dropped | zero_filled |
|---|---|---|---|---|
| 2005-06 | 1230 | 1230 | 0 | 0 |
| 2006-07 | 1230 | 1230 | 0 | 0 |
| 2007-08 | 1230 | 1230 | 0 | 0 |
| 2008-09 | 1230 | 1230 | 0 | 0 |
| 2009-10 | 1230 | 1230 | 0 | 0 |
| 2010-11 | 1230 | 1230 | 0 | 0 |
| 2011-12 | 990 | 990 | 0 | 12 |
| 2012-13 | 1229 | 1229 | 0 | 0 |
| 2013-14 | 1230 | 1230 | 0 | 0 |
| 2014-15 | 1230 | 1230 | 0 | 0 |
| 2015-16 | 1230 | 1230 | 0 | 0 |
| 2016-17 | 1230 | 1230 | 0 | 0 |
| 2017-18 | 1230 | 1230 | 0 | 0 |
| 2018-19 | 1230 | 1230 | 0 | 0 |
| 2019-20 | 1059 | 1059 | 0 | 0 |
| 2020-21 | 1080 | 1080 | 0 | 3 |
| 2021-22 | 1230 | 1230 | 0 | 0 |
| 2022-23 | 1230 | 1230 | 0 | 0 |
| 2023-24 | 1231 | 1231 | 0 | 0 |
| 2024-25 | 1231 | 1231 | 0 | 0 |
| 2025-26 | 1231 | 1231 | 0 | 0 |

Per-season data coverage (games with team stats / player box scores / inactive-player lists):

| season | games | has_team_stats | has_player_stats | has_inactives |
|---|---|---|---|---|
| 2005-06 | 1230 | 1230 | 1230 | 1208 |
| 2006-07 | 1230 | 1230 | 1230 | 1211 |
| 2007-08 | 1230 | 1230 | 1230 | 1222 |
| 2008-09 | 1230 | 1230 | 1230 | 1230 |
| 2009-10 | 1230 | 1230 | 1230 | 1230 |
| 2010-11 | 1230 | 1230 | 1230 | 1230 |
| 2011-12 | 990 | 990 | 990 | 980 |
| 2012-13 | 1229 | 1229 | 1229 | 1228 |
| 2013-14 | 1230 | 1230 | 1230 | 1230 |
| 2014-15 | 1230 | 1230 | 1230 | 1227 |
| 2015-16 | 1230 | 1230 | 1230 | 1230 |
| 2016-17 | 1230 | 1230 | 1230 | 1229 |
| 2017-18 | 1230 | 1230 | 1230 | 1230 |
| 2018-19 | 1230 | 1230 | 1230 | 1230 |
| 2019-20 | 1059 | 1059 | 1059 | 1059 |
| 2020-21 | 1080 | 1080 | 1080 | 1080 |
| 2021-22 | 1230 | 1230 | 1230 | 1229 |
| 2022-23 | 1230 | 1230 | 1230 | 1230 |
| 2023-24 | 1231 | 1231 | 1231 | 1230 |
| 2024-25 | 1231 | 1231 | 1231 | 1231 |
| 2025-26 | 1231 | 1231 | 1231 | 1231 |

Flags (not fixed):

- Inactive lists (`game_injuries`) are missing or partial in some seasons (see coverage table), so the injury features carry different information across seasons.
- Training/test use each game's box-score inactive list, while live serving uses the current injury report: same idea, different source.
- The player-value features use only box scores from days before the game, so no same-day leakage was found in them.
- `all` window starts at 2005-06 (first season with inactive lists), not 1990.
- LightGBM and MLP early stopping, and config selection, all use the inner validation season, so the validation log losses are slightly optimistic; test seasons are never used for tuning.

## Leaderboard (inner-selected, calibrated, ensembles, baselines), ranked by mean log loss

| role | family | config | window | weighting | logloss | ll_std | brier | acc | mean_diff | wins | vs_lr |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ensemble | ensemble | lr+lgbm+mlp | all | none | 0.6321 | 0.0153 | 0.2210 | 0.6402 | -0.0006 | 5 | tie |
| ensemble | ensemble | lr+lgbm+mlp | all | hl5 | 0.6323 | 0.0151 | 0.2211 | 0.6422 | -0.0003 | 6 | tie |
| baseline_lr | lr | plain_default | all | hl5 | 0.6326 | 0.0148 | 0.2211 | 0.6429 | 0.0000 | 0 | tie |
| ensemble | ensemble | lr+lgbm | all | none | 0.6326 | 0.0153 | 0.2212 | 0.6408 | -0.0001 | 4 | tie |
| ensemble | ensemble | lr+lgbm | all | hl5 | 0.6327 | 0.0151 | 0.2213 | 0.6394 | 0.0001 | 4 | tie |
| baseline_lr | lr | plain_default | all | none | 0.6328 | 0.0152 | 0.2212 | 0.6435 | 0.0000 | 0 | tie |
| baseline_lr | lr | plain_default | last5 | none | 0.6328 | 0.0142 | 0.2213 | 0.6425 | 0.0000 | 0 | tie |
| selected | lr | inner-selected | all | none | 0.6328 | 0.0152 | 0.2213 | 0.6421 | 0.0001 | 6 | tie |
| selected | lr | inner-selected | all | hl5 | 0.6329 | 0.0148 | 0.2213 | 0.6409 | 0.0003 | 5 | tie |
| baseline_lr | lr | plain_default | last5 | hl5 | 0.6329 | 0.0142 | 0.2213 | 0.6412 | 0.0000 | 0 | tie |
| ensemble | ensemble | lr+lgbm | all | hl2 | 0.6329 | 0.0150 | 0.2214 | 0.6385 | -0.0001 | 3 | tie |
| ensemble | ensemble | lr+lgbm+mlp | all | hl2 | 0.6330 | 0.0147 | 0.2214 | 0.6395 | -0.0001 | 5 | tie |
| baseline_lr | lr | plain_default | all | hl2 | 0.6330 | 0.0145 | 0.2213 | 0.6402 | 0.0000 | 0 | tie |
| baseline_lr | lr | plain_default | last8 | hl5 | 0.6330 | 0.0145 | 0.2213 | 0.6393 | 0.0000 | 0 | tie |
| selected | lr | inner-selected | last5 | none | 0.6331 | 0.0140 | 0.2214 | 0.6412 | 0.0003 | 5 | tie |
| ensemble | ensemble | lr+lgbm | last8 | hl5 | 0.6332 | 0.0149 | 0.2215 | 0.6385 | 0.0001 | 4 | tie |
| ensemble | ensemble | lr+lgbm | last8 | none | 0.6332 | 0.0149 | 0.2215 | 0.6406 | -0.0000 | 5 | tie |
| baseline_lr | lr | plain_default | last8 | none | 0.6332 | 0.0147 | 0.2214 | 0.6402 | 0.0000 | 0 | tie |
| baseline_lr | lr | plain_default | last8 | hl2 | 0.6333 | 0.0144 | 0.2215 | 0.6406 | 0.0000 | 0 | tie |
| calibrated_platt | lr | inner-selected | all | none | 0.6333 | 0.0154 | 0.2215 | 0.6394 | 0.0006 | 5 | tie |
| baseline_lr | lr | plain_default | last5 | hl2 | 0.6334 | 0.0144 | 0.2215 | 0.6410 | 0.0000 | 0 | tie |
| selected | lr | inner-selected | last8 | none | 0.6334 | 0.0145 | 0.2215 | 0.6396 | 0.0002 | 5 | tie |
| selected | lr | inner-selected | last8 | hl5 | 0.6334 | 0.0143 | 0.2216 | 0.6390 | 0.0004 | 5 | tie |
| selected | lr | inner-selected | last5 | hl5 | 0.6334 | 0.0140 | 0.2215 | 0.6399 | 0.0005 | 3 | tie |
| calibrated_platt | lr | inner-selected | all | hl5 | 0.6335 | 0.0152 | 0.2215 | 0.6397 | 0.0008 | 5 | tie |
| ensemble | ensemble | lr+lgbm | last5 | hl5 | 0.6335 | 0.0149 | 0.2217 | 0.6385 | 0.0006 | 4 | tie |
| ensemble | ensemble | lr+lgbm | last8 | hl2 | 0.6335 | 0.0149 | 0.2217 | 0.6390 | 0.0003 | 3 | tie |
| ensemble | ensemble | lr+lgbm+mlp | last8 | hl5 | 0.6336 | 0.0143 | 0.2217 | 0.6407 | 0.0005 | 4 | tie |
| selected | lr | inner-selected | all | hl2 | 0.6336 | 0.0141 | 0.2216 | 0.6399 | 0.0006 | 4 | tie |
| ensemble | ensemble | lr+lgbm | last5 | none | 0.6336 | 0.0149 | 0.2217 | 0.6384 | 0.0008 | 2 | tie |
| ensemble | ensemble | lr+lgbm+mlp | last8 | none | 0.6336 | 0.0146 | 0.2217 | 0.6392 | 0.0004 | 4 | tie |
| calibrated_platt | lr | inner-selected | last5 | none | 0.6336 | 0.0140 | 0.2216 | 0.6400 | 0.0008 | 5 | tie |
| ensemble | ensemble | lr+lgbm | last5 | hl2 | 0.6337 | 0.0150 | 0.2217 | 0.6379 | 0.0003 | 4 | tie |
| calibrated_platt | lr | inner-selected | all | hl2 | 0.6338 | 0.0146 | 0.2217 | 0.6408 | 0.0007 | 5 | tie |
| calibrated_platt | lr | inner-selected | last5 | hl5 | 0.6338 | 0.0141 | 0.2217 | 0.6411 | 0.0009 | 4 | tie |
| selected | lr | inner-selected | last8 | hl2 | 0.6338 | 0.0140 | 0.2217 | 0.6395 | 0.0005 | 5 | tie |
| selected | lr | inner-selected | last5 | hl2 | 0.6340 | 0.0141 | 0.2218 | 0.6394 | 0.0006 | 1 | tie |
| calibrated_platt | lr | inner-selected | last8 | hl5 | 0.6340 | 0.0147 | 0.2218 | 0.6400 | 0.0010 | 5 | tie |
| calibrated_platt | lr | inner-selected | last8 | none | 0.6340 | 0.0149 | 0.2218 | 0.6403 | 0.0009 | 5 | tie |
| ensemble | ensemble | lr+lgbm+mlp | last8 | hl2 | 0.6341 | 0.0144 | 0.2219 | 0.6406 | 0.0008 | 3 | tie |

## Recency: window x weighting per model family (inner-selected config, mean log loss)

### lr

| window | hl2 | hl5 | none |
|---|---|---|---|
| all | 0.6336 | 0.6329 | 0.6328 |
| last3 | 0.6353 | 0.6350 | 0.6349 |
| last5 | 0.6340 | 0.6334 | 0.6331 |
| last8 | 0.6338 | 0.6334 | 0.6334 |

Best: window=all, weighting=none (log loss 0.6328). Within 0.002 of best (ties): all/hl2, all/hl5, all/none, last5/hl2, last5/hl5, last5/none, last8/hl2, last8/hl5, last8/none.

### rf

| window | hl2 | hl5 | none |
|---|---|---|---|
| all | 0.6397 | 0.6428 | 0.6453 |
| last3 | 0.6405 | 0.6408 | 0.6408 |
| last5 | 0.6398 | 0.6403 | 0.6417 |
| last8 | 0.6400 | 0.6410 | 0.6428 |

Best: window=all, weighting=hl2 (log loss 0.6397). Within 0.002 of best (ties): all/hl2, last3/hl2, last3/hl5, last3/none, last5/hl2, last5/hl5, last8/hl2, last8/hl5.

### lgbm

| window | hl2 | hl5 | none |
|---|---|---|---|
| all | 0.6360 | 0.6362 | 0.6358 |
| last3 | 0.6383 | 0.6380 | 0.6383 |
| last5 | 0.6371 | 0.6374 | 0.6381 |
| last8 | 0.6367 | 0.6363 | 0.6365 |

Best: window=all, weighting=none (log loss 0.6358). Within 0.002 of best (ties): all/hl2, all/hl5, all/none, last5/hl2, last5/hl5, last8/hl2, last8/hl5, last8/none.

### mlp

| window | hl2 | hl5 | none |
|---|---|---|---|
| all | 0.6371 | 0.6362 | 0.6354 |
| last3 | 0.6423 | 0.6425 | 0.6423 |
| last5 | 0.6431 | 0.6412 | 0.6413 |
| last8 | 0.6396 | 0.6398 | 0.6405 |

Best: window=all, weighting=none (log loss 0.6354). Within 0.002 of best (ties): all/hl2, all/hl5, all/none.

Which config the inner validation season picked (count over all folds x windows x weightings):

| family | config | times_picked |
|---|---|---|
| lgbm | d3_lr0.03_mcs100 | 38 |
| lgbm | d3_lr0.03_mcs50 | 40 |
| lgbm | d4_lr0.03_mcs100 | 22 |
| lgbm | d4_lr0.03_mcs50 | 20 |
| lr | std_C0.01 | 58 |
| lr | std_C0.1 | 7 |
| lr | std_C1 | 55 |
| mlp | h16_a1e-2 | 8 |
| mlp | h32x16_a1e-2 | 26 |
| mlp | h64_a1e-1 | 47 |
| mlp | h64x32_a1e-1 | 39 |
| rf | current_n100 | 7 |
| rf | depth6_leaf50 | 113 |

## Per-config results (every config refit on the full window; descriptive only)

Config choice for the headline numbers above is made on the inner validation season, not from this table. Showing window=all, weighting=none; the full grid is in `results/config_summary.csv`.

| role | family | config | window | weighting | logloss | ll_std | brier | acc | mean_diff | wins | vs_lr |
|---|---|---|---|---|---|---|---|---|---|---|---|
| candidate | lr | std_C1 | all | none | 0.6327 | 0.0154 | 0.2212 | 0.6441 | -0.0000 | 6 | tie |
| candidate | lr | std_C0.1 | all | none | 0.6327 | 0.0153 | 0.2212 | 0.6427 | -0.0000 | 6 | tie |
| candidate | lr | plain_default | all | none | 0.6328 | 0.0152 | 0.2212 | 0.6435 | 0.0000 | 0 | tie |
| candidate | lr | std_C0.01 | all | none | 0.6329 | 0.0149 | 0.2213 | 0.6411 | 0.0002 | 4 | tie |
| candidate | mlp | h64_a1e-1 | all | none | 0.6346 | 0.0162 | 0.2221 | 0.6400 | 0.0018 | 2 | tie |
| candidate | lgbm | d4_lr0.03_mcs100 | all | none | 0.6349 | 0.0154 | 0.2222 | 0.6345 | 0.0021 | 3 | worse |
| candidate | lgbm | d4_lr0.03_mcs50 | all | none | 0.6352 | 0.0150 | 0.2224 | 0.6369 | 0.0025 | 3 | worse |
| candidate | mlp | h16_a1e-2 | all | none | 0.6353 | 0.0152 | 0.2224 | 0.6343 | 0.0025 | 2 | worse |
| candidate | mlp | h64x32_a1e-1 | all | none | 0.6354 | 0.0162 | 0.2224 | 0.6382 | 0.0026 | 2 | worse |
| candidate | lgbm | d3_lr0.03_mcs50 | all | none | 0.6356 | 0.0162 | 0.2225 | 0.6329 | 0.0028 | 1 | worse |
| candidate | lgbm | d3_lr0.03_mcs100 | all | none | 0.6358 | 0.0160 | 0.2226 | 0.6347 | 0.0030 | 1 | worse |
| candidate | mlp | h32x16_a1e-2 | all | none | 0.6372 | 0.0166 | 0.2230 | 0.6392 | 0.0044 | 0 | worse |
| candidate | rf | depth6_leaf50 | all | none | 0.6465 | 0.0101 | 0.2274 | 0.6247 | 0.0138 | 0 | worse |
| candidate | rf | current_n100 | all | none | 0.6467 | 0.0131 | 0.2274 | 0.6254 | 0.0140 | 0 | worse |
| candidate | rf | depth4_leaf100 | all | none | 0.6566 | 0.0105 | 0.2322 | 0.6077 | 0.0238 | 0 | worse |

## Calibration

Mean log loss across all window/weighting cells, uncalibrated (`selected`) vs calibrated on the inner validation season:

| family | calibrated_isotonic | calibrated_platt | selected |
|---|---|---|---|
| lgbm | 0.6493 | 0.6386 | 0.6371 |
| lr | 0.6441 | 0.6344 | 0.6338 |
| mlp | 0.6494 | 0.6400 | 0.6401 |
| rf | 0.6539 | 0.6418 | 0.6413 |

Reliability buckets for the best inner-selected model (lr, window=all, weighting=none), pooled across folds:

| bucket | n | avg_pred | actual |
|---|---|---|---|
| 0.0-0.1 | 4.0000 | 0.0821 | 0.2500 |
| 0.1-0.2 | 127.0000 | 0.1672 | 0.1890 |
| 0.2-0.3 | 588.0000 | 0.2591 | 0.2670 |
| 0.3-0.4 | 1253.0000 | 0.3556 | 0.3360 |
| 0.4-0.5 | 1895.0000 | 0.4519 | 0.4480 |
| 0.5-0.6 | 2585.0000 | 0.5506 | 0.5447 |
| 0.6-0.7 | 2567.0000 | 0.6488 | 0.6299 |
| 0.7-0.8 | 2003.0000 | 0.7475 | 0.7319 |
| 0.8-0.9 | 875.0000 | 0.8389 | 0.8183 |
| 0.9-1.0 | 85.0000 | 0.9177 | 0.8824 |

## Final per-model setup (each family on its own training window, no recency weighting)

Windows: lr=all, lgbm=all, mlp=all, rf=last5. Config per family is inner-selected on the validation season. `mean_diff` is against the default logistic regression on all history.

| role | name | logloss | ll_std | brier | acc | mean_diff | wins | vs_lr |
|---|---|---|---|---|---|---|---|---|
| ensemble | ensemble lr+lgbm+mlp | 0.6321 | 0.0153 | 0.2210 | 0.6402 | -0.0006 | 5 | tie |
| ensemble | ensemble lr+lgbm | 0.6326 | 0.0153 | 0.2212 | 0.6408 | -0.0001 | 4 | tie |
| ensemble | ensemble lr+rf+lgbm+mlp | 0.6327 | 0.0145 | 0.2212 | 0.6402 | -0.0000 | 5 | tie |
| baseline_lr | plain_default | 0.6328 | 0.0152 | 0.2212 | 0.6435 | 0.0000 | 0 | tie |
| selected | lr (all) | 0.6328 | 0.0152 | 0.2213 | 0.6421 | 0.0001 | 6 | tie |
| selected | mlp (all) | 0.6354 | 0.0157 | 0.2225 | 0.6386 | 0.0027 | 1 | worse |
| selected | lgbm (all) | 0.6358 | 0.0160 | 0.2227 | 0.6343 | 0.0031 | 2 | worse |
| selected | rf (last5) | 0.6417 | 0.0134 | 0.2253 | 0.6318 | 0.0090 | 0 | worse |
| baseline_home | const | 0.6866 | 0.0064 | 0.2467 | 0.5616 | 0.0538 | 0 | worse |
