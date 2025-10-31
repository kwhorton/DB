import pandas as pd

def standings(teams,schedule,all_tourneys,week):

    standings = []
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
    standings = sorted(standings, key=lambda d: (-d['score'], -d['fp'], -d['h2h']))
    
    # Group by division
    divisions = {}
    for team_standing in standings:
        division = team_standing['division']
        if division not in divisions:
            divisions[division] = []
        divisions[division].append(team_standing)

    divisions = dict(sorted(divisions.items()))
    
    return divisions

def get_player_ranks(teams,week):

    stats_for_week = []
    for team in teams:
        for player in team.players:
            week_stats = [stat for stat in player.all_stats if stat['Week']==week]
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
