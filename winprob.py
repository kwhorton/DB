"""Win probability by game state, learned from the saved game logs.

Every entry in game.log records the court right after a throw: who is
alive, who holds a ball and how many loose balls sit in each team's
reservoir. Before the next throw, loose balls go to live players without
one (Game.reassign_balls), so the state that decides the next throw is

    (alive, holding, loose)  for each side, seen from one team.

There are always 5 balls, so holding + loose over both sides is 5.

The table is the share of games won from each state. Every state is
counted from both teams' points of view, so the table is neutral (no home
edge) and P(state) + P(mirrored state) = 1. States seen only a few times
are shrunk toward a coarser state that ignores loose balls, and that one
toward the alive counts alone.

Each throw then has a value for the throwing team: the win probability
after it minus the win probability before it (win probability added).

Run `python winprob.py` for the table and what each throw result is worth.
"""
from collections import defaultdict
from dataclasses import dataclass

BALLS = 5

# Pseudo-games of the coarser state mixed into each state's win rate
SHRINK = 20


@dataclass(frozen=True)
class State:
    """The court before a throw, from one team's side ('us')."""
    alive: int
    holding: int
    loose: int
    opp_alive: int
    opp_holding: int
    opp_loose: int

    def mirrored(self):
        return State(self.opp_alive, self.opp_holding, self.opp_loose,
                     self.alive, self.holding, self.loose)

    @property
    def finished(self):
        return self.alive == 0 or self.opp_alive == 0

    @property
    def coarse(self):
        """Who's alive and who holds a ball, ignoring loose balls."""
        return (self.alive, self.holding, self.opp_alive, self.opp_holding)

    @property
    def counts(self):
        return (self.alive, self.opp_alive)


def _pick_up(alive, holding, loose):
    """Loose balls go to live players without one."""
    taken = min(loose, alive - holding)
    return holding + taken, loose - taken


def game_states(game):
    """[State] from players1's side: the opening court, then the court
    after each throw. The last state is the finished game."""
    side = {p.pid for p in game.players1}
    states = []
    for entry in game.log:
        alive = sum(pid in side for pid in entry['Alive'])
        holding = sum(pid in side for pid in entry['Holders'])
        opp_alive = len(entry['Alive']) - alive
        opp_holding = len(entry['Holders']) - holding
        holding, loose = _pick_up(alive, holding, entry['Reservoir1'])
        opp_holding, opp_loose = _pick_up(opp_alive, opp_holding, entry['Reservoir2'])
        states.append(State(alive, holding, loose, opp_alive, opp_holding, opp_loose))
    return states


class WinProb:
    """P(win | state), counted from a set of games."""

    def __init__(self, games):
        self.wins = defaultdict(int)
        self.seen = defaultdict(int)
        self.coarse_wins = defaultdict(int)
        self.coarse_seen = defaultdict(int)
        self.count_wins = defaultdict(int)
        self.count_seen = defaultdict(int)
        for game in games:
            won = game.winner == 1
            for state in game_states(game):
                if state.finished:
                    continue
                for s, w in ((state, won), (state.mirrored(), not won)):
                    self.wins[s] += w
                    self.seen[s] += 1
                    self.coarse_wins[s.coarse] += w
                    self.coarse_seen[s.coarse] += 1
                    self.count_wins[s.counts] += w
                    self.count_seen[s.counts] += 1

    def by_counts(self, alive, opp_alive):
        """Win rate by players alive alone."""
        if opp_alive == 0:
            return 1.0
        if alive == 0:
            return 0.0
        seen = self.count_seen[(alive, opp_alive)]
        return self.count_wins[(alive, opp_alive)] / seen if seen else 0.5

    def __call__(self, state):
        if state.finished:
            return 1.0 if state.opp_alive == 0 else 0.0
        p = self.by_counts(*state.counts)
        p = (self.coarse_wins[state.coarse] + SHRINK * p) / (self.coarse_seen[state.coarse] + SHRINK)
        return (self.wins[state] + SHRINK * p) / (self.seen[state] + SHRINK)


def throw_values(game, wp):
    """[(play, value)] for each throw in the game: the throwing team's win
    probability after the throw minus before it. The target's team loses
    the same amount."""
    states = game_states(game)
    team1 = {p.pid for p in game.players1}
    values = []
    for before, after, play in zip(states, states[1:], game.log[1:]):
        value = wp(after) - wp(before)
        if play['Thrower'] not in team1:
            value = -value
        values.append((play, value))
    return values


def all_games(all_tiers_data):
    return [game for data in all_tiers_data.values()
            for match in data['schedule'] for game in match.games]


if __name__ == '__main__':
    import pickle
    import random
    from player import *            # classes the pickle refers to
    from team import *
    from match import *
    from tourney import *
    from playoffs import *

    with open('season_all_tiers.pkl', 'rb') as f:
        games = all_games(pickle.load(f))
    wp = WinProb(games)
    print(f"{len(games)} games, {len(wp.seen)} distinct states")

    print("\nWin probability by players alive (rows: us, columns: them)")
    print("      " + "".join(f"{n:>6}" for n in range(1, 6)))
    for us in range(1, 6):
        print(f"{us:>6}" + "".join(f"{wp.by_counts(us, them):6.0%}" for them in range(1, 6)))

    print("\nAt 3 v 3, by balls (held + loose, us / them)")
    for s in sorted((s for s in wp.seen if s.counts == (3, 3)),
                    key=lambda s: (-s.holding - s.loose, -s.holding)):
        print(f"  {s.holding}+{s.loose} / {s.opp_holding}+{s.opp_loose}  "
              f"{wp(s):6.1%}  n={wp.seen[s]}")

    # What each throw result is worth to the throwing team
    by_result = defaultdict(list)
    catch_revive = {True: [], False: []}
    hit_by_count = defaultdict(list)
    for game in games:
        states = game_states(game)
        team1 = {p.pid for p in game.players1}
        for (play, value), before in zip(throw_values(game, wp), states):
            by_result[play['Result']].append(value)
            us = before if play['Thrower'] in team1 else before.mirrored()
            if play['Result'] == 'Catch':
                # the catcher's team brings someone back if anyone is out
                catch_revive[us.opp_alive < 5].append(value)
            elif play['Result'] == 'Hit':
                hit_by_count[(us.alive, us.opp_alive)].append(value)

    avg = lambda xs: sum(xs) / len(xs)
    hit = avg(by_result['Hit'])
    print("\nAverage win probability added, for the thrower's team")
    for result in ('Hit', 'Catch', 'Block', 'Miss'):
        v = by_result[result]
        print(f"  {result:6} {avg(v):+.3f}  ({avg(v) / hit:+.2f} hits)  n={len(v)}")
    for revive, v in catch_revive.items():
        label = 'brings a player back' if revive else 'nobody out to bring back'
        print(f"  Catch, {label}: {-avg(v):+.3f} to the catcher's team "
              f"({-avg(v) / hit:.2f} hits), n={len(v)}")

    print("\nValue of a hit by players alive (rows: thrower's team, columns: target's)")
    print("      " + "".join(f"{n:>7}" for n in range(1, 6)))
    for us in range(1, 6):
        print(f"{us:>6}" + "".join(f"{avg(hit_by_count[(us, them)]):+7.3f}"
                                    if hit_by_count[(us, them)] else "      -"
                                    for them in range(1, 6)))

    # Calibration: build on half the games, check predictions on the other half
    random.seed(0)
    random.shuffle(games)
    half = len(games) // 2
    train = WinProb(games[:half])
    bins = defaultdict(lambda: [0, 0])
    for game in games[half:]:
        for state in game_states(game):
            if not state.finished:
                b = bins[min(int(train(state) * 10), 9)]
                b[0] += game.winner == 1
                b[1] += 1
    print("\nCalibration on held-out games (predicted -> actual)")
    for i in sorted(bins):
        w, n = bins[i]
        print(f"  {i * 10:3}-{i * 10 + 10}%  {w / n:6.1%}  n={n}")
