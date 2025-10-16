import pandas as pd

def standings(teams,schedule,all_tourneys,week):

    standings = []
    end = (week>=3)*(week+1) + (week<3)*(2*week-2) + 1
    
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
    
    return divisions
