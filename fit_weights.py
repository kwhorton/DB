"""Fit the classic impact weights to the swap test's true impacts.

swap_test.py measures each regular player's true offense and defense:
how much their team's win rate drops when their aim and throw (offense)
or speed and hands (defense) are swapped for the tier average. This fits
the points per throw result that best predict those numbers from the
season's box score:

  offense   true offense per game ~ the player's throws per game that
            hit, were blocked, missed or were caught
  defense   true defense per game ~ throws at the player per game that
            they were hit by, blocked, dodged or caught

Rates are taken relative to the tier average, as the season race does.
Weights are scaled so a hit is worth 1 point to the thrower. Each tier is
also scored with weights fitted on the other three, so the comparison
with the current weights is on players the fit never saw.

    python swap_test.py      # writes swap_test_results.csv
    python fit_weights.py
"""
import csv
import math
from collections import defaultdict

import numpy as np

RESULTS = ('Hit', 'Block', 'Miss', 'Catch')


def event_rates(data):
    """{pid: {'games', 'offense': {result: per game}, 'defense': {...}}}
    over the regular season."""
    games = defaultdict(int)
    counts = defaultdict(lambda: {'offense': defaultdict(int), 'defense': defaultdict(int)})
    for match in data['schedule']:
        for game in match.games:
            for p in game.players1 + game.players2:
                games[p.pid] += 1
            for play in game.log:
                if play['Result'] is None:
                    continue
                counts[play['Thrower']]['offense'][play['Result']] += 1
                counts[play['Target']]['defense'][play['Result']] += 1
    return {pid: {'games': n,
                  **{side: {r: counts[pid][side][r] / n for r in RESULTS}
                     for side in ('offense', 'defense')}}
            for pid, n in games.items()}


def centred(rates, pids, side):
    """Per-game rates minus the tier's games-weighted average."""
    total = sum(rates[p]['games'] for p in rates)
    avg = {r: sum(rates[p][side][r] * rates[p]['games'] for p in rates) / total for r in RESULTS}
    return np.array([[rates[p][side][r] - avg[r] for r in RESULTS] for p in pids])


def fit(x, y):
    return np.linalg.lstsq(x, y, rcond=None)[0]


def correlation(a, b):
    return float(np.corrcoef(a, b)[0, 1])


if __name__ == '__main__':
    import pickle
    from player import *            # classes the pickle refers to
    from team import *
    from match import *
    from tourney import *
    from playoffs import *
    from awards import OFFENSE_WEIGHTS, DEFENSE_WEIGHTS

    with open('season_all_tiers.pkl', 'rb') as f:
        all_tiers_data = pickle.load(f)
    with open('swap_test_results.csv') as f:
        truth = list(csv.DictReader(f))

    current = {'offense': np.array([OFFENSE_WEIGHTS[r] for r in RESULTS]),
               'defense': np.array([DEFENSE_WEIGHTS[r] for r in RESULTS])}
    tiers = {}
    for tier, data in all_tiers_data.items():
        rows = [r for r in truth if r['tier'] == tier]
        pids = [r['pid'] for r in rows]
        rates = event_rates(data)
        tiers[tier] = {side: (centred(rates, pids, side),
                              np.array([float(r[f'true_{side}']) for r in rows]))
                       for side in ('offense', 'defense')}
        tiers[tier]['overall'] = np.array([float(r['true_overall']) for r in rows])

    # Every tier together
    weights = {side: fit(np.vstack([t[side][0] for t in tiers.values()]),
                         np.concatenate([t[side][1] for t in tiers.values()]))
               for side in ('offense', 'defense')}
    hit = weights['offense'][0]
    print("Fitted points per throw result (1 = a hit, to the thrower)")
    print(f"  {'':8}{'Offense (thrower)':>26}{'Defense (target)':>26}")
    print(f"  {'':8}{'fitted':>13}{'current':>13}{'fitted':>13}{'current':>13}")
    for i, r in enumerate(RESULTS):
        print(f"  {r:8}{weights['offense'][i] / hit:+13.2f}{current['offense'][i]:+13.2f}"
              f"{weights['defense'][i] / hit:+13.2f}{current['defense'][i]:+13.2f}")

    # Each tier scored with weights fitted on the other three
    print("\nCorrelation with true impact per game, each tier fitted on the other three")
    print(f"  {'':8}{'':10}{'current':>10}{'fitted':>10}")
    for tier, t in tiers.items():
        others = [o for name, o in tiers.items() if name != tier]
        scores = {}
        for side in ('offense', 'defense'):
            w = fit(np.vstack([o[side][0] for o in others]),
                    np.concatenate([o[side][1] for o in others]))
            w = w / fit(np.vstack([o['offense'][0] for o in others]),
                        np.concatenate([o['offense'][1] for o in others]))[0]
            x, y = t[side]
            scores[side] = (x @ current[side], x @ w)
            print(f"  {tier:8}{side:10}{correlation(scores[side][0], y):10.3f}"
                  f"{correlation(scores[side][1], y):10.3f}")
        overall = [scores['offense'][k] + scores['defense'][k] for k in (0, 1)]
        print(f"  {tier:8}{'overall':10}{correlation(overall[0], t['overall']):10.3f}"
              f"{correlation(overall[1], t['overall']):10.3f}")
