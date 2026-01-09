from match import *

def build_h2h_schedule(teams, year):

    #Week1a: E vs M, S vs W
    e_teams = [team for team in teams if team.division == "East"]
    e_teams_sorted = sorted(e_teams, key = lambda team: team.rating, reverse= True)
    m_teams = [team for team in teams if team.division == "Midwest"]
    m_teams_sorted = sorted(m_teams, key = lambda team: team.rating, reverse= True)
    s_teams = [team for team in teams if team.division == "South"]
    s_teams_sorted = sorted(s_teams, key = lambda team: team.rating, reverse= True)
    w_teams = [team for team in teams if team.division == "West"]
    w_teams_sorted = sorted(w_teams, key = lambda team: team.rating, reverse= True)

    matches = []
    for i in range(8):
        if (i % 2) == 0: 
            matches.append(Match(w_teams_sorted[7-i],s_teams_sorted[7-i],"H",year, 1.0))
            matches.append(Match(m_teams_sorted[7-i],e_teams_sorted[7-i],"H",year, 1.0))
        else:
            matches.append(Match(s_teams_sorted[7-i],w_teams_sorted[7-i],"H",year, 1.0))
            matches.append(Match(e_teams_sorted[7-i],m_teams_sorted[7-i],"H",year, 1.0))

    for i in range(8):
        if (i % 2) == 0: 
            matches.append(Match(w_teams_sorted[7-i],m_teams_sorted[7-i],"H",year, 1.5))
            matches.append(Match(s_teams_sorted[7-i],e_teams_sorted[7-i],"H",year, 1.5))
        else:
            matches.append(Match(m_teams_sorted[7-i],w_teams_sorted[7-i],"H",year, 1.5))
            matches.append(Match(e_teams_sorted[7-i],s_teams_sorted[7-i],"H",year, 1.5))

    for i in range(8):
        if (i % 2) == 0: 
            matches.append(Match(m_teams_sorted[7-i],s_teams_sorted[7-i],"H",year, 2.0))
            matches.append(Match(e_teams_sorted[7-i],w_teams_sorted[7-i],"H",year, 2.0))
        else:
            matches.append(Match(s_teams_sorted[7-i],m_teams_sorted[7-i],"H",year, 2.0))
            matches.append(Match(w_teams_sorted[7-i],e_teams_sorted[7-i],"H",year, 2.0))

    div_order = [7,1,5,3]
    for i in range(4):
        matches.append(Match(e_teams_sorted[div_order[i]],e_teams_sorted[7-div_order[i]],"H",year, 2.5))
        matches.append(Match(m_teams_sorted[7-div_order[i]],m_teams_sorted[div_order[i]],"H",year, 2.5))
        matches.append(Match(s_teams_sorted[div_order[i]],s_teams_sorted[7-div_order[i]],"H",year, 2.5))
        matches.append(Match(w_teams_sorted[7-div_order[i]],w_teams_sorted[div_order[i]],"H",year, 2.5))

    return matches
