import pandas as pd
from show_results import *
from league import H2H_WEEKS, TOURNEY_TYPES, FIRST_TOURNEY_WEEK, record_key, game_pct


WEEKS = H2H_WEEKS + list(range(FIRST_TOURNEY_WEEK, FIRST_TOURNEY_WEEK + len(TOURNEY_TYPES)))

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

def team_rating(team, rating_week):
    r = get_week_rating(team, rating_week)
    return sum(r.values()) / 4

def rating_week_for(week):
    """Week 0 has no all_stats entry; Week 1's entry holds start-of-season attributes."""
    return week if week >= 1 else 1

def ranked(teams, n, rating_week):
    """[(team, rating)] best first by record_key on the first n entries
    (score, tourney wins, H2H match wins, game win %). The rating is
    returned for display only; it never breaks ties."""
    rated = [(team, team_rating(team, rating_week)) for team in teams]
    rated.sort(key=lambda tr: record_key(tr[0].score[:n], tr[0].games[:n]))
    return rated

def game_pct_display(team, n):
    """Game win % through the first n entries, or None before any games."""
    games = team.games[:n]
    return game_pct(games) if games else None

def division_place(team, teams, n, rating_week):
    div = ranked((t for t in teams if t.division == team.division), n, rating_week)
    return [t.team_name for t, _ in div].index(team.team_name) + 1


def get_standings_by_division(teams, schedule, all_tourneys, week):
    """Generate standings organized by division"""
    n = results_through(week)      # number of score entries through this week
    rw = rating_week_for(week)     # Week 0 -> Week 1 entry (start of season)

    # Group by division (teams stay in ranked order within each division)
    divisions = {}
    for team, rating in ranked(teams, n, rw):
        s = team.score[:n]
        divisions.setdefault(team.division, []).append({
            'team_name': team.team_name,
            'division': team.division,
            'rating': rating,
            'score': sum(s),
            'fp': s.count(21),
            'h2h': s[:4].count(15),
            'gpct': game_pct_display(team, n)
        })

    return dict(sorted(divisions.items()))

def get_playoff_standings(teams, schedule, all_tourneys, current_week):
    """Calculate playoff standings with division leaders and wildcards"""
    n = results_through(current_week)     # number of score entries through this week
    rw = rating_week_for(current_week)    # Week 0 -> Week 1 entry (start of season)

    division_leaders = []
    wildcards = []
    seen_divisions = set()
    for team, rating in ranked(teams, n, rw):
        s = team.score[:n]
        record = {
            'team': team,
            'division': team.division,
            'score': sum(s),
            'fp': s.count(21),
            'h2h': s[:4].count(15),
            'gpct': game_pct_display(team, n),
            'rating': rating,
            'is_leader': team.division not in seen_divisions
        }
        seen_divisions.add(team.division)
        (division_leaders if record['is_leader'] else wildcards).append(record)

    # Division leaders first (in ranked order), then everyone else
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
