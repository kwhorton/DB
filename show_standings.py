import pandas as pd
from show_results import *


def standings(teams,schedule,all_tourneys,week):

    standings = []
    # For week 0 (preseason), show no results (end=0)
    if week == 0:
        end = 0
    else:
        end = (week>=3)*(week+1) + (week<3)*(2*week-2) + 1
        end = int(end)
    for team in teams:

        output = {'Team': team.team_name,
                  'Division': team.division,
                  'Rating': team.get_team_rating_week(week),
                  'Score': sum(team.score[0:end]),
                  'FP': team.score[0:end].count(21),
                  'H2H': team.score[0:min(4,end)].count(15)
                  }


        standings.append(output)

    standings = sorted(standings, key = lambda d: (-d['Score'], -d['FP'], -d['H2H']))

    df = pd.DataFrame(standings)
    df['Team'] = df['Team'].apply(lambda team_name: f'<a href="/team/{team_name}">{team_name}</a>')
    standings_html = df.to_html(escape = False,index=False)

    return standings_html

        
def get_standings_by_division(teams, schedule, all_tourneys, week):
    """Generate standings organized by division"""
    standings = []
    # For week 0 (preseason), show no results
    if week == 0:
        end = 0
    else:
        end = (week >= 3) * (week + 1) + (week < 3) * (2 * week - 2) + 1
        end = int(end)
    for team in teams:
        output = {
            'team_name': team.team_name,
            'division': team.division,
            'rating': team.get_team_rating_week(week),
            'score': sum(team.score[0:end]),
            'fp': team.score[0:end].count(21),
            'h2h': team.score[0:min(4, end)].count(15)
        }
        standings.append(output)
    
    # Sort by score, then FP, then H2H
    standings = sorted(standings, key=lambda d: (-d['score'], -d['fp'], -d['h2h'], -d['rating']))
    
    # Group by division
    divisions = {}
    for team_standing in standings:
        division = team_standing['division']
        if division not in divisions:
            divisions[division] = []
        divisions[division].append(team_standing)

    divisions = dict(sorted(divisions.items()))
    
    return divisions

def get_playoff_standings(teams, schedule, all_tourneys, current_week):
    """Calculate playoff standings with division leaders and wildcards"""
    # Calculate the end index based on current week
    display_week = current_week
    # For week 0 (preseason), show no results
    if display_week == 0:
        end = 0
    else:
        end = (display_week>=3)*(display_week+1) + (display_week<3)*(2*display_week-2) + 1
        end = int(end)
    
    # Get division leaders
    divisions = {}
    for team in teams:
        if team.division not in divisions:
            divisions[team.division] = []
        divisions[team.division].append(team)
    
    # Sort teams within each division
    division_leaders = []
    for division_name, division_teams in divisions.items():

        all_div_teams_sorted = []
        for team in division_teams:
            div_team_data = {
                'team': team,
                'division': team.division,
                'score': sum(team.score[0:end]),
                'fp': team.score[0:end].count(21),
                'h2h': team.score[0:min(4, end)].count(15),
                'rating': team.get_team_rating_week(display_week),
                'is_leader': False
            }
            all_div_teams_sorted.append(div_team_data)

        # Sort all teams in division
        all_div_teams_sorted.sort(key=lambda x: (-x['score'], -x['fp'], -x['h2h'], -x['rating']))
                
        div_leader_data = all_div_teams_sorted[0]
        division_leaders.append(div_leader_data)
##
##        division_teams.sort(key=lambda t: (
##            -sum(t.score[0:end]),
##            -t.score[0:end].count(21),
##            -t.score[0:min(4, end)].count(15)
##        ))
##        if division_teams:
##            leader = division_teams[0]
##
##            division_leaders.append({
##                'team': leader,
##                'division': division_name,
##                'score': sum(leader.score[0:end]),
##                'fp': leader.score[0:end].count(21),
##                'h2h': leader.score[0:min(4, end)].count(15),
##                'rating': team.get_team_rating_week(display_week),
##                'is_leader': True
##            })
##    
    # Sort division leaders by score
    division_leaders.sort(key=lambda x: (-x['score'], -x['fp'], -x['h2h'],-x['rating']))
    
    # Get all teams sorted for wildcard
    all_teams_sorted = []
    for team in teams:
     #   team_rating = get_week_rating(team, display_week)
     #   avg_rating = 0.25 * (team_rating['Aim'] + team_rating['Speed'] + 
     #                       team_rating['Throw'] + team_rating['Hands'])
        team_data = {
            'team': team,
            'division': team.division,
            'score': sum(team.score[0:end]),
            'fp': team.score[0:end].count(21),
            'h2h': team.score[0:min(4, end)].count(15),
            'rating': team.get_team_rating_week(display_week),
            'is_leader': False
        }
        all_teams_sorted.append(team_data)
    
    # Sort all teams
    all_teams_sorted.sort(key=lambda x: (-x['score'], -x['fp'], -x['h2h'], -x['rating']))
    
    # Create playoff standings: division leaders first, then remaining teams
    playoff_standings = []
    division_leader_names = [leader['team'].team_name for leader in division_leaders]
    
    # Add division leaders
    for leader in division_leaders:
        leader['is_leader'] = True
        playoff_standings.append(leader)
    
    # Add remaining teams (wildcards)
    for team_data in all_teams_sorted:
        if team_data['team'].team_name not in division_leader_names:
            playoff_standings.append(team_data)
    
    return playoff_standings


def get_player_ranks(teams,week):

    stats_for_week = []
    for team in teams:
        for player in team.players:
            week_stats = [stat for stat in player.all_stats if stat['Week']==max(1,week)]
            week_stats = week_stats[0]
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
    df['aim_rank'] = df['aim'].rank(ascending=False, method='min')
    df['speed_rank'] = df['speed'].rank(ascending=False, method='min')
    df['throw_rank'] = df['throw'].rank(ascending=False, method='min')
    df['hands_rank'] = df['hands'].rank(ascending=False, method='min')
    df['total_rank'] = df['total'].rank(ascending=False, method='min')

    # Add division ranks
    for stat in ['aim', 'speed', 'throw', 'hands', 'total']:
        df[f'{stat}_div_rank'] = df.groupby('division')[stat].rank(ascending=False, method='min')

    # Convert back to list of dictionaries if needed
    stats_for_week = df.to_dict('records')

    return stats_for_week

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
