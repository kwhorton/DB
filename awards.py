"""Player impact scores and awards, computed from the saved game logs.

Every throw in game.log scores for two players: the thrower earns offense
points and the target earns defense points. Overall = offense + defense.

  Match MVP       best overall impact on the winning team
  Tournament MVP  best overall impact across a tournament, from any team,
                  plus a bonus for each match won
  Season race     points above the tier average: a player's season-to-date
                  impact minus what an average player would have earned in
                  the same number of games. The average is recalculated from
                  the games played through the selected week, so standings
                  never depend on later results.

Everything is ranked within a tier. Playoff games are kept out of the season
race and only feed the playoff awards.

Run `python awards.py` for a summary of each tier in the saved season.
"""
from collections import defaultdict
from dataclasses import dataclass

# Points per throw result, from the thrower's side and the target's side.
# A Miss is a dodge for the target; a Block is a blocked throw for the
# thrower and a successful block for the target.
OFFENSE_WEIGHTS = {'Hit': 1.0, 'Block': 0.15, 'Miss': -0.05, 'Catch': -1.25}
DEFENSE_WEIGHTS = {'Catch': 1.5, 'Block': 0.3, 'Miss': 0.1, 'Hit': -0.6}

# Tournament and playoff MVPs: bonus for each match won by the player's team
# in which the player appeared
MATCH_WIN_BONUS = 0.5

# Weeks counted in the "hot" column of the season race
HOT_WEEKS = 3

KINDS = ('overall', 'offense', 'defense')

# Rate stats only rank players who played at least this share of their
# team's games, so bench players can't lead on a handful of throws
QUALIFY_SHARE = 0.4

# Stat leader categories: (key, label, group, display format, needs to qualify)
STAT_CATEGORIES = [
    ('hits',          'Hits',            'Offense', 'int',    False),
    ('hits_per_game', 'Hits per Game',   'Offense', 'dec',    True),
    ('hit_rate',      'Hit Rate',        'Offense', 'pct',    True),
    ('accuracy',      'Accuracy',        'Offense', 'pct',    True),
    ('catches',       'Catches',         'Defense', 'int',    False),
    ('catch_rate',    'Catch Rate',      'Defense', 'pct',    True),
    ('dodge_rate',    'Dodge Rate',      'Defense', 'pct',    True),
    ('survival_rate', 'Survival Rate',   'Defense', 'pct',    True),
    ('rating',        'Overall Rating',  'Ratings', 'rating', False),
    ('aim',           'Aim',             'Ratings', 'rating', False),
    ('speed',         'Speed',           'Ratings', 'rating', False),
    ('throw',         'Throw',           'Ratings', 'rating', False),
    ('hands',         'Hands',           'Ratings', 'rating', False),
    ('improvement',   'Most Improved',   'Ratings', 'signed', False),
]


@dataclass
class Impact:
    offense: float = 0.0
    defense: float = 0.0
    games: int = 0

    @property
    def overall(self):
        return self.offense + self.defense

    def get(self, kind):
        return getattr(self, kind)

    def add(self, other):
        self.offense += other.offense
        self.defense += other.defense
        self.games += other.games


def game_impact(game):
    """{pid: Impact} for one game. Everyone on court counts one game played,
    whether or not they threw or were targeted."""
    impact = {player.pid: Impact(games=1) for player in game.players1 + game.players2}
    for play in game.log:
        result = play['Result']
        if result is None:          # opening entry, before any throw
            continue
        impact[play['Thrower']].offense += OFFENSE_WEIGHTS[result]
        impact[play['Target']].defense += DEFENSE_WEIGHTS[result]
    return impact


def sum_impacts(impacts):
    """Merge {pid: Impact} dicts into one."""
    total = defaultdict(Impact)
    for impact in impacts:
        for pid, line in impact.items():
            total[pid].add(line)
    return total


def match_impact(match):
    """{pid: Impact} summed over the games of one match."""
    return sum_impacts(game_impact(game) for game in match.games)


def _rate(num, den):
    return num / den if den else None


def _rank(rows, key):
    """Set row['rank'] by key, best first; tied rows share a rank."""
    ordered = sorted(rows, key=key)
    for i, row in enumerate(ordered):
        tied = i > 0 and key(row)[0] == key(ordered[i - 1])[0]
        row['rank'] = ordered[i - 1]['rank'] if tied else i + 1
    return ordered


def match_mvp(match):
    """The winning team's best overall impact in this match, as
    {'pid', 'team', 'impact'}; ties go to offense. None if unplayed."""
    if match.winner is None:
        return None
    winners = match.team1 if match.winner == 1 else match.team2
    impact = match_impact(match)
    candidates = [p.pid for p in winners.players if p.pid in impact]
    if not candidates:
        return None
    pid = min(candidates, key=lambda p: (-impact[p].overall, -impact[p].offense, p))
    return {'pid': pid, 'team': winners, 'impact': impact[pid]}


def event_leaders(matches, win_bonus=MATCH_WIN_BONUS):
    """Ranked rows for a set of matches (a tournament, a playoff round...):
    overall impact plus win_bonus for every match won in which the player
    appeared. The first row is the event MVP."""
    lines = defaultdict(Impact)
    wins = defaultdict(int)
    team_of, players = {}, {}
    for match in matches:
        impact = match_impact(match)
        winners = match.get_wl_teams()[0]
        for team in (match.team1, match.team2):
            for player in team.players:
                if player.pid not in impact:
                    continue
                team_of[player.pid] = team
                players[player.pid] = player
                lines[player.pid].add(impact[player.pid])
                if team is winners:
                    wins[player.pid] += 1

    rows = [{'pid': pid, 'player': players[pid], 'team': team_of[pid], 'impact': line,
             'match_wins': wins[pid],
             'score': line.overall + win_bonus * wins[pid]}
            for pid, line in lines.items()]
    return _rank(rows, key=lambda r: (-r['score'], -r['impact'].offense, r['pid']))


def tournament_mvp(tourney):
    rows = event_leaders(tourney.matches)
    return rows[0] if rows else None


def playoff_mvp(playoff_rounds):
    """MVP across every playoff round."""
    rows = event_leaders([m for rnd in playoff_rounds for m in rnd.matches])
    return rows[0] if rows else None


class TierAwards:
    """Season-to-date impact for one tier. Built once per tier when the app
    loads; results for each (week, kind) are cached."""

    def __init__(self, teams, schedule):
        self.teams = teams
        self.team_of = {p.pid: team for team in teams for p in team.players}
        self.player_of = {p.pid: p for team in teams for p in team.players}
        self.weeks = sorted({m.week for m in schedule})
        self.by_week = {week: defaultdict(Impact) for week in self.weeks}
        self.team_games = {week: defaultdict(int) for week in self.weeks}
        for match in schedule:
            for pid, line in match_impact(match).items():
                self.by_week[match.week][pid].add(line)
            for team in (match.team1, match.team2):
                self.team_games[match.week][team.team_name] += len(match.games)
        self._race = {}

    def weeks_through(self, week):
        return [w for w in self.weeks if w <= week]

    def totals_through(self, week):
        """{pid: Impact} over all regular-season games through week."""
        return sum_impacts(self.by_week[w] for w in self.weeks_through(week))

    @staticmethod
    def baseline(totals, kind):
        """Tier average impact per game played."""
        games = sum(line.games for line in totals.values())
        return sum(line.get(kind) for line in totals.values()) / games if games else 0.0

    def season_race(self, week, kind='overall'):
        """Every player in the tier, ranked by points above the tier average
        through week. Each row: pid, player, team, division, games, total,
        per_game, above_avg, rank and div_rank, prev_rank and prev_div_rank
        (last week's, None in the first week), move and div_move (places
        gained since last week) and hot (points above average over the last
        HOT_WEEKS weeks)."""
        weeks = self.weeks_through(week)
        if not weeks:
            return []
        week = weeks[-1]            # a selected week between game weeks
        if (week, kind) in self._race:
            return self._race[(week, kind)]

        totals = self.totals_through(week)
        avg = self.baseline(totals, kind)
        recent = sum_impacts(self.by_week[w] for w in weeks[-HOT_WEEKS:])

        rows = []
        for pid, team in self.team_of.items():
            line = totals.get(pid, Impact())
            hot = recent.get(pid, Impact())
            rows.append({
                'pid': pid,
                'player': self.player_of[pid],
                'team': team,
                'division': team.division,
                'games': line.games,
                'total': line.get(kind),
                'per_game': line.get(kind) / line.games if line.games else None,
                'above_avg': line.get(kind) - avg * line.games,
                'hot': hot.get(kind) - avg * hot.games,
            })
        rows = _rank(rows, key=lambda r: (-r['above_avg'], -r['games'], r['pid']))

        for division in {r['division'] for r in rows}:
            div_rows = [r for r in rows if r['division'] == division]
            for i, row in enumerate(div_rows):
                tied = i > 0 and row['above_avg'] == div_rows[i - 1]['above_avg']
                row['div_rank'] = div_rows[i - 1]['div_rank'] if tied else i + 1

        prev = {r['pid']: r for r in self.season_race(weeks[-2], kind)} if len(weeks) > 1 else {}
        for row in rows:
            last = prev.get(row['pid'])
            row['prev_rank'] = last['rank'] if last else None
            row['prev_div_rank'] = last['div_rank'] if last else None
            row['move'] = row['prev_rank'] - row['rank'] if last else 0
            row['div_move'] = row['prev_div_rank'] - row['div_rank'] if last else 0

        self._race[(week, kind)] = rows
        return rows

    def player_of_week(self, week, kind='overall', division=None):
        """Ranked rows for one week alone, scored above that week's own tier
        average. Optionally limited to one division (ranks stay tier-wide)."""
        if week not in self.by_week:
            return []
        lines = self.by_week[week]
        avg = self.baseline(lines, kind)
        rows = [{'pid': pid, 'player': self.player_of[pid], 'team': self.team_of[pid],
                 'division': self.team_of[pid].division,
                 'games': line.games, 'total': line.get(kind),
                 'above_avg': line.get(kind) - avg * line.games}
                for pid, line in lines.items()]
        rows = _rank(rows, key=lambda r: (-r['above_avg'], -r['games'], r['pid']))
        return [r for r in rows if division is None or r['division'] == division]

    def stat_lines(self, week):
        """One row per player of regular-season counting stats and rates
        through week (from player.all_stats), plus ratings as of week."""
        weeks = set(self.weeks_through(week))
        team_games = defaultdict(int)
        for w in weeks:
            for name, games in self.team_games[w].items():
                team_games[name] += games
        rating_week = max(week, 1)  # Week 1's entry holds start-of-season ratings

        rows = []
        for pid, player in self.player_of.items():
            team = self.team_of[pid]
            played = [s for s in player.all_stats if s['Week'] in weeks]
            tot = {k: sum(s[k] for s in played) for k in
                   ('GP', 'Throws', 'Hits', 'Blocked', 'Caught',
                    'Targeted', 'Hit', 'Blocks', 'Catches')}
            rated = [s for s in player.all_stats if s['Week'] <= rating_week]
            now = rated[-1] if rated else player.get_start_stats()
            ratings = {k.lower(): now[k] for k in ('Aim', 'Speed', 'Throw', 'Hands')}
            start = player.get_start_stats()

            contacts_for = tot['Hits'] + tot['Blocked'] + tot['Caught']
            contacts_against = tot['Hit'] + tot['Blocks'] + tot['Catches']
            rows.append({
                'pid': pid, 'player': player, 'team': team, 'division': team.division,
                'games': tot['GP'],
                'qualified': tot['GP'] > 0 and tot['GP'] >= QUALIFY_SHARE * team_games[team.team_name],
                'hits': tot['Hits'],
                'hits_per_game': _rate(tot['Hits'], tot['GP']),
                'hit_rate': _rate(tot['Hits'], tot['Throws']),
                'accuracy': _rate(contacts_for, tot['Throws']),
                'catches': tot['Catches'],
                'catch_rate': _rate(tot['Catches'], tot['Targeted']),
                'dodge_rate': _rate(tot['Targeted'] - contacts_against, tot['Targeted']),
                'survival_rate': _rate(tot['Targeted'] - tot['Hit'], tot['Targeted']),
                **ratings,
                'rating': sum(ratings.values()) / 4,
                'improvement': (sum(ratings.values()) - sum(start.values())) / 4,
            })
        return rows

    def stat_leaders(self, week, division=None, top=5):
        """The top players in each STAT_CATEGORIES category, ranked within
        the tier or within one division: [{key, label, group, fmt, qualify,
        rows}], each row with rank, player, team and value."""
        lines = [r for r in self.stat_lines(week)
                 if division is None or r['division'] == division]
        leaders = []
        for key, label, group, fmt, qualify in STAT_CATEGORIES:
            rows = [{'pid': r['pid'], 'player': r['player'], 'team': r['team'],
                     'games': r['games'], 'value': r[key]}
                    for r in lines
                    if r[key] is not None and (r['qualified'] or not qualify)]
            # Zero hits, catches or improvement isn't worth listing
            if key in ('hits', 'catches', 'improvement'):
                rows = [r for r in rows if r['value'] > 0]
            rows = _rank(rows, key=lambda r: (-r['value'], -r['games'], r['pid']))
            leaders.append({'key': key, 'label': label, 'group': group, 'fmt': fmt,
                            'qualify': qualify, 'rows': rows[:top]})
        return leaders


if __name__ == '__main__':
    import pickle
    from player import *            # classes the pickle refers to
    from team import *
    from match import *
    from tourney import *
    from playoffs import *

    with open('season_all_tiers.pkl', 'rb') as f:
        all_tiers_data = pickle.load(f)

    for tier_name, data in all_tiers_data.items():
        awards = TierAwards(data['teams'], data['schedule'])
        last = awards.weeks[-1]
        print(f"\n{'=' * 60}\n{tier_name}\n{'=' * 60}")
        for kind in KINDS:
            print(f"Season race ({kind}) through Week {last}:")
            for r in awards.season_race(last, kind)[:5]:
                print(f"  {r['rank']:2}. {r['pid']}  {r['team'].team_name:14} "
                      f"GP {r['games']:3}  per game {r['per_game']:+.2f}  "
                      f"above avg {r['above_avg']:+6.1f}  ({r['move']:+d})")
        top = awards.player_of_week(last)[0]
        print(f"Player of Week {last}: {top['pid']} ({top['team'].team_name}) "
              f"{top['above_avg']:+.1f} above avg")
        for tourney in [t for t in data['all_tourneys'] if t.week == last]:
            mvp = tournament_mvp(tourney)
            champ = tourney.finish_order[0].team_name
            print(f"Week {last} tournament won by {champ}: MVP {mvp['pid']} "
                  f"({mvp['team'].team_name}, {mvp['match_wins']} match wins, "
                  f"score {mvp['score']:.1f})")
        first = data["schedule"][0]
        mvp = match_mvp(first)
        print(f"Week {first.week} {first.team1.team_name} vs {first.team2.team_name}: "
              f"MVP {mvp['pid']} ({mvp['team'].team_name}) {mvp['impact'].overall:+.1f}")
        if data.get('playoff_rounds'):
            mvp = playoff_mvp(data['playoff_rounds'])
            print(f"Playoff MVP: {mvp['pid']} ({mvp['team'].team_name}) score {mvp['score']:.1f}")
