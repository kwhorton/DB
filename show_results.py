import pandas as pd

def results(team_name,teams,schedule,all_tourneys,week):
    team_results = []
    # For week 0 (preseason), show no results
    if week == 0:
        end = 0
    else:
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
            


def get_week_rating(team,week):
    team_stats ={'Aim':0,
                 'Speed':0,
                 'Throw':0,
                 'Hands':0}
    
    for player in team.players:
        player_week = [stats for stats in player.all_stats if stats['Week'] == max(1,week)]
        player_week = player_week[0]
        team_stats['Aim']+=player_week['Aim']
        team_stats['Speed']+=player_week['Speed']
        team_stats['Throw']+=player_week['Throw']
        team_stats['Hands']+=player_week['Hands']

    team_stats['Aim']=team_stats['Aim']/len(team.players)
    team_stats['Speed']=team_stats['Speed']/len(team.players)
    team_stats['Throw']=team_stats['Throw']/len(team.players)
    team_stats['Hands']=team_stats['Hands']/len(team.players)

    return team_stats

def get_season_schedule(team_name, teams, schedule, all_tourneys):
    """Get the season schedule for a team (for Week 0 preview)"""
    schedule_data = []
    tourney_types = ['Random','Random','Division','Division','Score','Random',
                 'Division','Division','Score','Random','Random','Score','Division',
                 'Division']
    
    # Get head-to-head matches (weeks 1, 1.5, 2, 2.5)
    for week in [1, 1.5, 2, 2.5]:
        team_match = [match1 for match1 in schedule if match1.week == week and 
                     (match1.team1.team_name == team_name or match1.team2.team_name == team_name)]
        if team_match:
            match = team_match[0]
            opponent = match.team1.team_name if match.team2.team_name == team_name else match.team2.team_name
            atvs = 'at' if match.team1.team_name == team_name else 'vs'
            schedule_data.append({
                'Week': week,
                'Event': f"{atvs} {opponent}",
                'Type': 'Head-to-Head'
            })
    
    # Add tournament weeks (weeks 3-16)
    for week_idx, tourney_type in enumerate(tourney_types):
        schedule_data.append({
            'Week': week_idx + 3,
            'Event': f"{tourney_type} Tournament",
            'Type': 'Tournament'
        })
    
    import pandas as pd
    df = pd.DataFrame(schedule_data)
    schedule_html = df.to_html(index=False)
    
    return schedule_html


