import pandas as pd

def results(team_name,teams,schedule,all_tourneys,week):
    team_results = []
    end = (week>=3)*(week+1) + (week<3)*(2*week-2) + 1
    end = int(end)
    tourney_types = ['Random','Random','Division','Division','Score','Random',
                 'Division','Division','Score','Random','Random','Score','Division',
                 'Division']
    teamobj = [team for team in teams if team.team_name == team_name]
    teamobj = teamobj[0]
    for w in range(end):
        if w < 4:
            team_match = [match1 for match1 in schedule if match1.week == (w/2)+1 and (match1.team1.team_name == team_name or match1.team2.team_name==team_name)]
            team_match = team_match[0]
            opponent = team_match.team1.team_name if team_match.team2.team_name == team_name else team_match.team2.team_name
            atvs = 'at' if team_match.team1.team_name == team_name else 'vs'
            set_win = team_match.match_score[0] if team_match.team1.team_name == team_name else team_match.match_score[1]
            set_loss = team_match.match_score[1] if team_match.team1.team_name == team_name else team_match.match_score[0]
            output = {'Week': (w/2)+1,
                      'Event': f"{atvs} {opponent}",
                      'Result': f"{"W" if set_win == 3 else "L"} ({set_win}-{set_loss})",
                      'Score': teamobj.score[w]}
            team_results.append(output)
                      
        else:
            
            if 8-teamobj.score[w]/3 >= 4:
                nth = "th"
            elif 8-teamobj.score[w]/3 ==3:
                nth = "rd"
            elif 8-teamobj.score[w]/3 == 2:
                nth = "nd"
            else:
                nth = "st"
            output = {'Week': w-1,
                      'Event': tourney_types[w-4],
                      'Result': f"{int(8-teamobj.score[w]/3)}{nth}",
                      'Score': teamobj.score[w]}
            team_results.append(output)
    df = pd.DataFrame(team_results)
    results_html = df.to_html(index=False)

    return results_html
            



