import pandas as pd
from show_results import *


WEEKS = [1, 1.5, 2, 2.5] + list(range(3, 17))

def results_before(week):
    """Number of team.score entries from weeks strictly before `week`."""
    if week <= 0:
        return 0
    return int(2*week - 2) if week < 3 else int(week + 1)

def results_through(week):
    """Number of team.score entries from weeks up to and including `week`."""
    if week <= 0:
        return 0
    return int(2*week - 1) if week < 3 else int(week + 2)

def snapshot(week_num, current_week):
    """(n_results, rating_week): each team entering week_num,
    limited to what's known as of current_week."""
    if week_num <= current_week:
        return results_before(week_num), week_num
    next_wk = next(w for w in WEEKS if w > current_week)
    return results_through(current_week), next_wk

def division_place(team, teams, n):
    div = [t for t in teams if t.division == team.division]
    div.sort(key=lambda t: (-sum(t.score[:n]),
                            -t.score[:n].count(21),
                            -t.score[:min(4, n)].count(15)))
    return [t.team_name for t in div].index(team.team_name) + 1

def team_rating(team, rating_week):
    r = get_week_rating(team, rating_week)
    return sum(r.values()) / 4

def rating_week_for(week):
    """Week 0 has no all_stats entry; Week 1's entry holds start-of-season attributes."""
    return week if week >= 1 else 1

def standings_key(team, n, rating_week):
    """Sort key: score, tourney wins (21s), H2H match wins (15s in first 4), rating."""
    s = team.score[:n]
    return (-sum(s),
            -s.count(21),
            -team.score[:min(4, n)].count(15),
            -team_rating(team, rating_week))

def division_place(team, teams, n, rating_week):
    div = sorted((t for t in teams if t.division == team.division),
                 key=lambda t: standings_key(t, n, rating_week))
    return [t.team_name for t in div].index(team.team_name) + 1


def standings(teams,schedule,all_tourneys,week):

    n = results_through(week)      # number of score entries through this week
    rw = rating_week_for(week)     # Week 0 -> Week 1 entry (start of season)

    standings = []
    # For week 0 (preseason), show no results 
    for team in teams:
        s = team.score[:n]
        output = {'Team': team.team_name,
                  'Division': team.division,
                  'Rating': team_rating(team, rw),
                  'Score': sum(s),
                  'FP': s.count(21),
                  'H2H': team.score[0:min(4,n)].count(15)
                  }

        standings.append(output)

    # Sort by score, tourney wins, H2H match wins, then rating
    standings = sorted(standings, key=lambda d: (-d['Score'], -d['FP'], -d['H2H'], -d['Rating']))

    df = pd.DataFrame(standings)
    df['Team'] = df['Team'].apply(lambda team_name: f'<a href="/team/{team_name}">{team_name}</a>')
    standings_html = df.to_html(escape = False,index=False)

    return standings_html

        
def get_standings_by_division(teams, schedule, all_tourneys, week):
    """Generate standings organized by division"""
    n = results_through(week)      # number of score entries through this week
    rw = rating_week_for(week)     # Week 0 -> Week 1 entry (start of season)

    standings = []
    for team in teams:
        s = team.score[:n]
        standings.append({
            'team_name': team.team_name,
            'division': team.division,
            'rating': team_rating(team, rw),
            'score': sum(s),
            'fp': s.count(21),
            'h2h': team.score[:min(4, n)].count(15)
        })

    # Score, tourney wins, H2H match wins, then rating
    standings.sort(key=lambda d: (-d['score'], -d['fp'], -d['h2h'], -d['rating']))

    # Group by division (teams stay in sorted order within each division)
    divisions = {}
    for team_standing in standings:
        divisions.setdefault(team_standing['division'], []).append(team_standing)

    return dict(sorted(divisions.items()))

def get_playoff_standings(teams, schedule, all_tourneys, current_week):
    """Calculate playoff standings with division leaders and wildcards"""
    n = results_through(current_week)     # number of score entries through this week
    rw = rating_week_for(current_week)    # Week 0 -> Week 1 entry (start of season)

    # Build each team's record once
    records = []
    for team in teams:
        s = team.score[:n]
        records.append({
            'team': team,
            'division': team.division,
            'score': sum(s),
            'fp': s.count(21),
            'h2h': team.score[:min(4, n)].count(15),
            'rating': team_rating(team, rw),
            'is_leader': False
        })

    # Score, tourney wins, H2H match wins, then rating
    sort_key = lambda r: (-r['score'], -r['fp'], -r['h2h'], -r['rating'])
    records.sort(key=sort_key)
    
    # Sort teams within each division
    division_leaders = []
    seen_divisions = set()
    for r in records:
        if r['division'] not in seen_divisions:
            seen_divisions.add(r['division'])
            r['is_leader'] = True
            division_leaders.append(r)

    # Division leaders first (already in sorted order), then everyone else
    wildcards = [r for r in records if not r['is_leader']]

    return division_leaders + wildcards


def get_player_ranks(teams,week):

    rw = rating_week_for(week)     # Week 0 -> Week 1 entry (start of season)

    stats_for_week = []
    for team in teams:
        for player in team.players:
            week_stats = next(stat for stat in player.all_stats if stat['Week'] == rw)
            player_info = {
                'pid': player.pid,
                'division': team.division,
                'aim': week_stats['Aim'],
                'speed': week_stats['Speed'],
                'throw': week_stats['Throw'],
                'hands': week_stats['Hands']
                }
            player_info['total'] = 0.25*(player_info['aim']+player_info['speed']+player_info['throw']+player_info['hands'])
            stats_for_week.append(player_info)

    # Convert to DataFrame for easier ranking
    df = pd.DataFrame(stats_for_week)

    # Add overall ranks (lower rank = better performance)
    for stat in ['aim', 'speed', 'throw', 'hands', 'total']:
        df[f'{stat}_rank'] = df[stat].rank(ascending=False, method='min')
        df[f'{stat}_div_rank'] = df.groupby('division')[stat].rank(ascending=False, method='min')

    return df.to_dict('records')

def ordinal(n):
    """
    Return the ordinal representation of a number (1 -> 1st, 2 -> 2nd, etc.)
    """
    n = int(n)
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
