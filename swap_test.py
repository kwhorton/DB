"""Swap-in test: how well each impact score tracks a player's true impact.

The simulation knows what really drives results (each player's ratings),
so a player's true impact can be measured directly: replay games they
played with the same teammates and opponents, once as they were and once
with the player swapped for an average player of the tier, and see how
much the win rate changes. Swapping only aim and throw for the tier
average measures their offense; only speed and hands, their defense.

Each score's per-game points above the tier average is then compared
with these true impacts across the tier's regular players. Both scores
come from the same games, so they share the same luck; the better score
is the one that tracks true impact more closely.

    python swap_test.py [games per player] [replays per game]

Ratings are the week's ratings from player.all_stats, the home team gets
its 10 point edge, and fatigue within a match is left out. Paired replays
share random numbers, so the gap between them is the swap, not luck.
"""
import csv
import math
import random
import sys
from collections import defaultdict
from multiprocessing import Pool

from game import Game

GAMES_PER_PLAYER = 60
REPLAYS = 80
MIN_GAMES = 100             # players with fewer games aren't tested
HOME_EDGE = 10              # match.py's home team bonus
ATTRS = ('Aim', 'Speed', 'Throw', 'Hands')
SWAPS = {'overall': ATTRS, 'offense': ('Aim', 'Throw'), 'defense': ('Speed', 'Hands')}


class SimPlayer:
    """Just what Game needs: a pid and four ratings."""

    def __init__(self, pid, ratings):
        self.pid = pid
        self.aim, self.speed, self.throw, self.hands = (ratings[a] for a in ATTRS)


def week_ratings(players, weeks):
    """{(pid, week): ratings} and the tier average {week: ratings}, weighted
    by games played that week."""
    ratings, avg = {}, {}
    for week in weeks:
        totals, games = defaultdict(float), 0
        for p in players:
            stats = next((s for s in p.all_stats if s['Week'] == week), None)
            if stats is None:
                continue
            ratings[(p.pid, week)] = {a: stats[a] for a in ATTRS}
            for a in ATTRS:
                totals[a] += stats[a] * stats['GP']
            games += stats['GP']
        avg[week] = {a: totals[a] / games for a in ATTRS}
    return ratings, avg


def jobs_for_tier(data, rng):
    """{pid: [game setups]}: the player's side, slot, both lineups' ratings,
    the tier average and the home edge, for a sample of their games."""
    players = [p for team in data['teams'] for p in team.players]
    weeks = sorted({m.week for m in data['schedule']})
    ratings, avg = week_ratings(players, weeks)
    played = defaultdict(list)
    for match in data['schedule']:
        home = match.match_type == 'H'
        for game in match.games:
            sides = [[ratings[(p.pid, match.week)] for p in game.players1],
                     [ratings[(p.pid, match.week)] for p in game.players2]]
            for side, lineup in enumerate((game.players1, game.players2)):
                for slot, p in enumerate(lineup):
                    played[p.pid].append((side, slot, sides, avg[match.week], home))
    return {pid: rng.sample(games, min(GAMES_PER_PLAYER, len(games)))
            for pid, games in played.items() if len(games) >= MIN_GAMES}


def _lineups(sides, home, side, slot, swap, average):
    lineups = []
    for s, lineup in enumerate(sides):
        team = []
        for i, r in enumerate(lineup):
            r = dict(r)
            if s == side and i == slot:
                for a in swap:
                    r[a] = average[a]
            if home and s == 1:
                r = {a: v + HOME_EDGE for a, v in r.items()}
            team.append(SimPlayer(f'{s}{i}', r))
        lineups.append(team)
    return lineups


def true_impact(args):
    """(pid, {kind: win rate as is minus win rate with the swap})."""
    pid, setups, replays, seed = args
    arms = {'as is': ()} | SWAPS
    wins = dict.fromkeys(arms, 0)
    for g, (side, slot, sides, average, home) in enumerate(setups):
        for r in range(replays):
            for arm, swap in arms.items():
                random.seed(hash((seed, g, r)))
                players1, players2 = _lineups(sides, home, side, slot, swap, average)
                game = Game(players1, players2)
                game.run_game()
                wins[arm] += game.winner == side + 1
    n = len(setups) * replays
    return pid, {kind: (wins['as is'] - wins[kind]) / n for kind in SWAPS}


def correlation(xs, ys):
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sxy / math.sqrt(sxx * syy)


def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0] * len(xs)
    for k, i in enumerate(order):
        r[i] = k
    return r


if __name__ == '__main__':
    import pickle
    from player import *            # classes the pickle refers to
    from team import *
    from match import *
    from tourney import *
    from playoffs import *
    from awards import TierAwards, WinProbScoring, KINDS

    games_per_player = int(sys.argv[1]) if len(sys.argv) > 1 else GAMES_PER_PLAYER
    replays = int(sys.argv[2]) if len(sys.argv) > 2 else REPLAYS
    GAMES_PER_PLAYER = games_per_player

    with open('season_all_tiers.pkl', 'rb') as f:
        all_tiers_data = pickle.load(f)
    win_prob = WinProbScoring([game for data in all_tiers_data.values()
                               for match in data['schedule'] for game in match.games])

    rng = random.Random(2033)
    rows = []
    with Pool() as pool:
        for tier, data in all_tiers_data.items():
            jobs = jobs_for_tier(data, rng)
            print(f"{tier}: simulating {len(jobs)} players...", flush=True)
            truth = dict(pool.map(true_impact, [(pid, setups, replays, i)
                                                for i, (pid, setups) in enumerate(jobs.items())]))
            scores = {}
            for name, scoring in (('classic', None), ('win_prob', win_prob)):
                awards = (TierAwards(data['teams'], data['schedule']) if scoring is None else
                          TierAwards(data['teams'], data['schedule'], scoring=scoring))
                last = awards.weeks[-1]
                for kind in KINDS:
                    for r in awards.season_race(last, kind):
                        scores[(name, kind, r['pid'])] = r['above_avg'] / r['games'] if r['games'] else 0
            for pid, true in truth.items():
                row = {'tier': tier, 'pid': pid}
                for kind in KINDS:
                    row[f'true_{kind}'] = true[kind]
                    for name in ('classic', 'win_prob'):
                        row[f'{name}_{kind}'] = scores[(name, kind, pid)]
                rows.append(row)

    out = 'swap_test_results.csv'
    with open(out, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    se = math.sqrt(2 * 0.25 / (games_per_player * replays))
    print(f"\n{len(rows)} players, {games_per_player} games x {replays} replays each "
          f"(true impact accurate to about +/-{se:.3f} wins per game or better)")
    print("\nCorrelation with true impact per game (Pearson / rank), within each tier")
    print(f"  {'':8}{'':10}{'Classic':>16}{'Win Prob':>16}")
    for tier in all_tiers_data:
        tier_rows = [r for r in rows if r['tier'] == tier]
        for kind in KINDS:
            true = [r[f'true_{kind}'] for r in tier_rows]
            cells = []
            for name in ('classic', 'win_prob'):
                score = [r[f'{name}_{kind}'] for r in tier_rows]
                cells.append(f"{correlation(score, true):.3f} / {correlation(ranks(score), ranks(true)):.3f}")
            print(f"  {tier:8}{kind:10}{cells[0]:>16}{cells[1]:>16}")

    print("\nTop 10 by true impact also in each score's top 10")
    for tier in all_tiers_data:
        tier_rows = [r for r in rows if r['tier'] == tier]
        line = []
        for kind in KINDS:
            top = lambda key: {r['pid'] for r in sorted(tier_rows, key=lambda r: -r[key])[:10]}
            true = top(f'true_{kind}')
            line.append(f"{kind} {len(true & top(f'classic_{kind}'))} vs {len(true & top(f'win_prob_{kind}'))}")
        print(f"  {tier}: " + ",  ".join(line) + "   (classic vs win prob)")
    print(f"\nPer-player results in {out}")
