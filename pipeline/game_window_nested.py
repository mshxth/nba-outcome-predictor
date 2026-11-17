"""Window-size search for the game-count rolling features (run from the repo root).

For each candidate set of game windows, fits logistic regression on the 10 test seasons
(all prior history). Each season also records the validation-season log loss, so a window
can be chosen without looking at the test season (the "nested pick"). Writes results/game_windows_nested*.csv.

Usage: NBA_DB_PATH=~/nba-data/nba_data_full.db python3 pipeline/game_window_nested.py
"""
import os, sys
os.environ['DROP_INJURIES'] = '1'
sys.path.insert(0, 'pipeline'); sys.path.insert(0, 'backend')
import numpy as np, pandas as pd
import game_window_experiment as gw
import model_comparison as mc
df, _ = mc.load_features(11)
tests = [s for s in sorted(df['season'].unique()) if s >= mc.FIRST_TEST_SEASON]
cands = {'days 7+30': None, 'g(10,30)': (10, 30), 'g(15,40)': (15, 40), 'g(20,40)': (20, 40), 'g(10,40)': (10, 40),
         'g(10,60)': (10, 60), 'g(20,)': (20,), 'g(30,)': (30,), 'g(20,60)': (20, 60), 'g(40,)': (40,)}
recs = []
for name, w in cands.items():
    frame = df if w is None else gw.blended_frame(df, w)[0]
    for t in tests:
        r, _ = mc.run_task(frame, t, 'all', 'none', families=['lr'])
        sel = [x for x in r if x['role'] == 'selected'][0]
        recs.append(dict(cand=name, season=t, val=sel['val_logloss'], test=sel['logloss'], acc=sel['acc']))
d = pd.DataFrame(recs)
summ = d.groupby('cand', sort=False).agg(val=('val', 'mean'), test=('test', 'mean'), acc=('acc', 'mean')).round(4)
base = d[d.cand == 'days 7+30'].set_index('season').test
summ['diff_vs_days'] = [round((d[d.cand == c].set_index('season').test - base).mean(), 4) for c in summ.index]
summ['seasons_better'] = [int(((d[d.cand == c].set_index('season').test - base) < 0).sum()) for c in summ.index]
print(summ.to_string())
# honest estimate: each season picks the candidate with the lowest VALIDATION logloss, then reports its TEST logloss
pick = d.loc[d.groupby('season').val.idxmin()].set_index('season')
print('\nnested pick (validation season chooses the window):')
print(pick[['cand', 'val', 'test']].round(4).to_string())
print('nested mean test logloss:', round(pick.test.mean(), 4), '| days 7+30 baseline:', round(base.mean(), 4),
      '| better in', int((pick.test < base).sum()), 'of', len(pick))
d.to_csv('results/game_windows_nested.csv', index=False)
