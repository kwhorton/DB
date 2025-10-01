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
    df['Team'] = df['Team'].apply(lambda team_name: f'<a href="/team_name/{team_name}">{team_name}</a>')
    standings_html = df.to_html(escape = False,index=False)

    return standings_html

        
