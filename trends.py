"""Week-by-week series for the charts on the player and team pages.

Each builder returns {'labels': [week labels], 'metrics': [metric, ...]},
where a metric is

    {'id', 'group', 'label', 'description',
     'format':  'int' | 'dec1' | 'dec2' | 'signed1' | 'signed3' | 'pct' | 'rank',
     'invert':  True for ranks (1st at the top),
     'domain':  optional [min, max] for the y axis,
     'zero_line': draw a baseline at 0,
     'series':  [{'name', 'values', 'role'}]}

and a series role is 'primary' (colored, in the legend), 'context' (the
other teams in a division, drawn thin and gray) or 'reference' (a tier
average, dashed). Values line up with labels; None means no data that week
(the player didn't play, say), which the chart draws as a gap.

Only weeks up to the selected current week are included, and only the
regular season, so nothing here gives away later results.
"""
from awards import KINDS
from league import record_key, game_pct
from show_standings import WEEKS, results_through, results_before
from show_results import get_week_rating

ATTRIBUTES = ('Aim', 'Speed', 'Throw', 'Hands')
KIND_NAMES = {'overall': 'Overall', 'offense': 'Offense', 'defense': 'Defense'}


def week_label(week):
    return f"{week:g}"


def _div(num, den):
    return num / den if den else None


def _metric(id, group, label, description, fmt, series, invert=False,
            domain=None, zero_line=False):
    return {'id': id, 'group': group, 'label': label, 'description': description,
            'format': fmt, 'invert': invert, 'domain': domain,
            'zero_line': zero_line, 'series': series}


def _series(name, values, role='primary'):
    return {'name': name, 'values': values, 'role': role}


# --------------------------------------------------------------------------
# Players
# --------------------------------------------------------------------------

# Per-game counting stats and rates: (id, label, description, format,
# function of a stats total dict -> value)
PLAYER_STATS = [
    ('hits_pg', 'Hits per game', 'Opponents hit per game played.', 'dec2',
     lambda s: _div(s['Hits'], s['GP'])),
    ('throws_pg', 'Throws per game', 'Throws per game played.', 'dec2',
     lambda s: _div(s['Throws'], s['GP'])),
    ('hit_rate', 'Hit rate', 'Share of throws that hit an opponent.', 'pct',
     lambda s: _div(s['Hits'], s['Throws'])),
    ('accuracy', 'Accuracy', 'Share of throws that made contact (hit, blocked or caught).', 'pct',
     lambda s: _div(s['Hits'] + s['Blocked'] + s['Caught'], s['Throws'])),
    ('catches_pg', 'Catches per game', 'Throws caught per game played.', 'dec2',
     lambda s: _div(s['Catches'], s['GP'])),
    ('hit_by_pg', 'Times hit per game', 'Times hit per game played (lower is better).', 'dec2',
     lambda s: _div(s['Hit'], s['GP'])),
    ('dodge_rate', 'Dodge rate', 'Share of throws at this player that missed entirely.', 'pct',
     lambda s: _div(s['Targeted'] - s['Hit'] - s['Blocks'] - s['Catches'], s['Targeted'])),
    ('survival_rate', 'Survival rate', 'Share of throws at this player that did not hit them.', 'pct',
     lambda s: _div(s['Targeted'] - s['Hit'], s['Targeted'])),
]

STAT_KEYS = ('GP', 'Throws', 'Hits', 'Blocked', 'Caught', 'Targeted', 'Hit', 'Blocks', 'Catches')


def player_trends(awards, pid, current_week):
    """Chart data for one player, or None before any games are played."""
    weeks = awards.weeks_through(current_week)
    if not weeks:
        return None
    player = awards.player_of[pid]
    stats_by_week = {s['Week']: s for s in player.all_stats}
    labels = [week_label(w) for w in weeks]

    # Impact: season to date (the race) and each week on its own, both
    # measured against the tier average for the same number of games
    race_above = {kind: [] for kind in KINDS}
    race_rank = {kind: [] for kind in KINDS}
    weekly_above = {kind: [] for kind in KINDS}
    for w in weeks:
        lines = awards.by_week[w]
        line = lines.get(pid)
        for kind in KINDS:
            row = next(r for r in awards.season_race(w, kind) if r['pid'] == pid)
            played = row['games'] > 0
            race_above[kind].append(round(row['above_avg'], 2) if played else None)
            race_rank[kind].append(row['rank'] if played else None)
            if line and line.games:
                avg = awards.baseline(lines, kind)
                weekly_above[kind].append(round(line.get(kind) - avg * line.games, 2))
            else:
                weekly_above[kind].append(None)

    metrics = [
        _metric('impact_season', 'Impact', 'Season impact above average',
                'Season-to-date impact points above what an average player would have '
                'earned in the same games. This is the MVP race score.',
                'signed1', [_series(KIND_NAMES[k], race_above[k]) for k in KINDS],
                zero_line=True),
        _metric('impact_week', 'Impact', 'Weekly impact above average',
                "Each week's impact points above that week's tier average.",
                'signed1', [_series(KIND_NAMES[k], weekly_above[k]) for k in KINDS],
                zero_line=True),
        _metric('race_rank', 'Impact', 'MVP race rank',
                'Place in the tier-wide season races (1st is the leader).',
                'rank', [_series(KIND_NAMES[k], race_rank[k]) for k in KINDS],
                invert=True),
    ]

    # Ratings entering each week, and play against the matchups
    week_stats = [stats_by_week.get(w) for w in weeks]
    metrics.append(_metric(
        'ratings', 'Ratings', 'Attributes',
        'Attribute ratings entering each week. Ratings rise or fall with performance.',
        'dec1', [_series(a, [s[a] if s else None for s in week_stats]) for a in ATTRIBUTES]))
    metrics.append(_metric(
        'ratings_avg', 'Ratings', 'Average rating',
        'Mean of Aim, Speed, Throw and Hands entering each week.',
        'dec1', [_series('Average', [round(sum(s[a] for a in ATTRIBUTES) / 4, 1) if s else None
                                     for s in week_stats])]))
    metrics.append(_metric(
        'perf', 'Ratings', 'Performance vs. expected',
        'How each skill played against what the matchups predicted that week; above 0 '
        'beat expectations. Aim and Throw are offense, Speed and Hands defense.',
        'signed3', [_series(a, [s[f'{a}_Perf'] if s and s['GP'] else None for s in week_stats])
                    for a in ATTRIBUTES], zero_line=True))

    # Weekly stats, beside the tier average for the same week
    tier_totals = {}
    for w in weeks:
        totals = dict.fromkeys(STAT_KEYS, 0)
        for p in awards.player_of.values():
            s = next((s for s in p.all_stats if s['Week'] == w), None)
            if s:
                for k in STAT_KEYS:
                    totals[k] += s[k]
        tier_totals[w] = totals
    for id, label, description, fmt, fn in PLAYER_STATS:
        mine = [fn(s) if s and s['GP'] else None for s in week_stats]
        tier = [fn(tier_totals[w]) for w in weeks]
        metrics.append(_metric(
            id, 'Weekly stats', label, description, fmt,
            [_series('This player', [_round(v) for v in mine]),
             _series('Tier average', [_round(v) for v in tier], role='reference')]))

    return {'labels': labels, 'metrics': metrics}


def _round(v, digits=4):
    return round(v, digits) if v is not None else None


# --------------------------------------------------------------------------
# Teams
# --------------------------------------------------------------------------

def team_trends(team, teams, awards, current_week):
    """Chart data for one team, or None before any games are played."""
    weeks = [w for w in WEEKS if w <= current_week]
    if not weeks:
        return None
    labels = [week_label(w) for w in weeks]
    division = [t for t in teams if t.division == team.division]
    rivals = sorted((t for t in division if t is not team), key=lambda t: t.team_name)

    def by_week(fn):
        """{team: [fn(team, n) for each week]}, n = score entries through it."""
        return {t: [fn(t, results_through(w)) for w in weeks] for t in teams}

    def ordered(n, pool):
        return sorted(pool, key=lambda t: record_key(t.score[:n], t.games[:n]))

    points = by_week(lambda t, n: sum(t.score[:n]))
    gpct = by_week(lambda t, n: round(game_pct(t.games[:n]) * 100, 1) if t.games[:n] else None)
    div_place, tier_place = {t: [] for t in teams}, []
    for w in weeks:
        n = results_through(w)
        for place, t in enumerate(ordered(n, division), start=1):
            div_place[t].append(place)
        tier_place.append(ordered(n, teams).index(team) + 1)

    weekly = {t: [sum(t.score[results_before(w):results_through(w)]) for w in weeks] for t in teams}
    tier_avg_weekly = [round(sum(weekly[t][i] for t in teams) / len(teams), 2)
                       for i in range(len(weeks))]

    def with_rivals(values):
        return ([_series(team.team_name, values[team])] +
                [_series(t.team_name, values[t], role='context') for t in rivals])

    metrics = [
        _metric('points', 'Standings', 'Points',
                f'Season points to date, against the rest of the {team.division} division.',
                'int', with_rivals(points)),
        _metric('points_week', 'Standings', 'Points gained per week',
                'Points earned each week, beside the tier average.',
                'int', [_series(team.team_name, weekly[team]),
                        _series('Tier average', tier_avg_weekly, role='reference')]),
        _metric('div_rank', 'Standings', 'Division rank',
                f'Place in the {team.division} division after each week.',
                'rank', with_rivals(div_place), invert=True, domain=[1, len(division)]),
        _metric('tier_rank', 'Standings', 'Tier rank',
                'Place among every team in the tier after each week.',
                'rank', [_series(team.team_name, tier_place)], invert=True,
                domain=[1, len(teams)]),
        _metric('gpct', 'Standings', 'Game win %',
                f'Share of games won to date, against the rest of the {team.division} division.',
                'dec1', with_rivals(gpct)),
    ]

    # Roster impact: the team's players summed, each against the tier average
    impact = {kind: [] for kind in KINDS}
    roster = {p.pid for p in team.players}
    for w in weeks:
        lines = awards.by_week.get(w, {})
        for kind in KINDS:
            avg = awards.baseline(lines, kind) if lines else 0
            total = sum(line.get(kind) - avg * line.games
                        for pid, line in lines.items() if pid in roster)
            impact[kind].append(round(total, 2) if lines else None)
    metrics.append(_metric(
        'impact_week', 'Roster', 'Team impact above average',
        "The roster's combined impact points each week, above the tier average.",
        'signed1', [_series(KIND_NAMES[k], impact[k]) for k in KINDS], zero_line=True))

    ratings = [get_week_rating(team, w) for w in weeks]
    metrics.append(_metric(
        'ratings', 'Roster', 'Team ratings',
        'Roster average of each attribute entering each week.',
        'dec1', [_series(a, [round(r[a], 1) for r in ratings]) for a in ATTRIBUTES]))

    return {'labels': labels, 'metrics': metrics}
