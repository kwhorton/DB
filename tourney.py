from match import *
from league import record_key
import random

class Tournament:

    def __init__(self, team_list,year,week):

        self.team_list = team_list
        self.year = year
        self.week = week
        self.matches = []
        self.finish_order = []
        

    def run_tourney(self):
        
        self.team_list.sort(key=lambda t: record_key(t.score, t.games))
        
        # Round 1
        #1 v 8
        match1 = Match(self.team_list[0],self.team_list[7],"T", self.year, self.week)
        match1.run_match()
        self.matches.append(match1)

        #4 v 5
        match2 = Match(self.team_list[3],self.team_list[4],"T", self.year, self.week)
        match2.run_match()
        self.matches.append(match2)

        #3 v 6
        match3 = Match(self.team_list[2],self.team_list[5],"T", self.year, self.week)
        match3.run_match()
        self.matches.append(match3)

        #2 v 7
        match4 = Match(self.team_list[1],self.team_list[6],"T", self.year, self.week)
        match4.run_match()
        self.matches.append(match4)


        # Round 2 (losers bracket)
        #L1 vs L2
        match5 = Match(match1.get_wl_teams()[1],match2.get_wl_teams()[1],"T", self.year, self.week)
        match5.run_match()
        self.matches.append(match5)


        #L3 vs L4
        match6 = Match(match3.get_wl_teams()[1],match4.get_wl_teams()[1],"T", self.year, self.week)
        match6.run_match()
        self.matches.append(match6)

        # Round 3a (7 vs 8)
        #L5 vs L6
        match7 = Match(match5.get_wl_teams()[1],match6.get_wl_teams()[1],"T", self.year, self.week)
        match7.run_match()
        self.matches.append(match7)


        # Round 3b (main bracket)
        #W1 vs W2
        match8 = Match(match1.get_wl_teams()[0],match2.get_wl_teams()[0],"T", self.year, self.week)
        match8.run_match()
        self.matches.append(match8)

        #W3 vs W4
        match9 = Match(match3.get_wl_teams()[0],match4.get_wl_teams()[0],"T", self.year, self.week)
        match9.run_match()
        self.matches.append(match9)
        

        # Round 4 (losers bracket)
        #W5 vs L8
        match10 = Match(match5.get_wl_teams()[0],match8.get_wl_teams()[1],"T", self.year, self.week)
        match10.run_match()
        self.matches.append(match10)

        #W5 vs L9
        match11 = Match(match6.get_wl_teams()[0],match9.get_wl_teams()[1],"T", self.year, self.week)
        match11.run_match()
        self.matches.append(match11)


        # Round 5a (5 vs 6)
        #L10 vs L11
        match12 = Match(match10.get_wl_teams()[1],match11.get_wl_teams()[1],"T", self.year, self.week)
        match12.run_match()
        self.matches.append(match12)
        

        # Round 5b (losers bracket)
        #W10 vs W11
        match13 = Match(match10.get_wl_teams()[0],match11.get_wl_teams()[0],"T", self.year, self.week)
        match13.run_match()
        self.matches.append(match13)


        # Round 5c (main bracket)
        #W8 vs W9
        match14 = Match(match8.get_wl_teams()[0],match9.get_wl_teams()[0],"T", self.year, self.week)
        match14.run_match()
        self.matches.append(match14)


        # Round 6 (losers bracket)
        #W13 vs L14
        match15 = Match(match13.get_wl_teams()[0],match14.get_wl_teams()[1],"T", self.year, self.week)
        match15.run_match()
        self.matches.append(match15)


        # Round 7 (main bracket - Final)
        #W14 vs W15
        match16 = Match(match14.get_wl_teams()[0],match15.get_wl_teams()[0],"T", self.year, self.week)
        match16.run_match()
        self.matches.append(match16)

        if match16.get_wl_teams()[0] == match15.get_wl_teams()[0]:
            # Round 7b (main bracket - final game 2)
            #W16 vs L16
            match17 = Match(match16.get_wl_teams()[0],match16.get_wl_teams()[1],"T", self.year, self.week)
            match17.run_match()
            self.matches.append(match17)
            self.finish_order.append(match17.get_wl_teams()[0])
            self.finish_order.append(match17.get_wl_teams()[1])
        else:
            self.finish_order.append(match16.get_wl_teams()[0])
            self.finish_order.append(match16.get_wl_teams()[1])

        self.finish_order.append(match15.get_wl_teams()[1])
        self.finish_order.append(match13.get_wl_teams()[1])
        self.finish_order.append(match12.get_wl_teams()[0])
        self.finish_order.append(match12.get_wl_teams()[1])
        self.finish_order.append(match7.get_wl_teams()[0])
        self.finish_order.append(match7.get_wl_teams()[1])

        self.finish_order[0].score.append(21)
        self.finish_order[1].score.append(18)
        self.finish_order[2].score.append(15)
        self.finish_order[3].score.append(12)
        self.finish_order[4].score.append(9)
        self.finish_order[5].score.append(6)
        self.finish_order[6].score.append(3)
        self.finish_order[7].score.append(0)

        # This week's game record, alongside the score entry just added
        for team in self.team_list:
            team.games.append(game_record(team, self.matches))


def get_tourney_list(teams,tourney_type):

    divisions = [[team for team in teams if team.division == div]
                 for div in ["East", "Midwest", "South", "West"]]

    if tourney_type == "Division":
        return divisions

    # Random / Score: each group of 8 takes two teams from every division
    for div_teams in divisions:
        if tourney_type == "Random":
            random.shuffle(div_teams)
        elif tourney_type == "Score":
            div_teams.sort(key=lambda t: record_key(t.score, t.games))

    return [[team for div_teams in divisions for team in div_teams[2*g:2*g+2]]
            for g in range(4)]

def backfill_game_records(teams, schedule, all_tourneys):
    """Rebuild team.games for seasons pickled before it was saved: one
    (won, played) pair per score entry, i.e. each H2H match in week order,
    then each week's tournament."""
    for team in teams:
        if hasattr(team, 'games'):
            continue
        h2h = sorted((m for m in schedule
                      if m.match_type == "H" and team in (m.team1, m.team2)),
                     key=lambda m: m.week)
        tourneys = sorted((t for t in all_tourneys if team in t.team_list),
                          key=lambda t: t.week)
        team.games = ([game_record(team, [m]) for m in h2h] +
                      [game_record(team, t.matches) for t in tourneys])

def subtype_of(tourney, all_tourneys):
    """tourney.subtype, derived the way main.py sets it for seasons pickled
    before subtype was saved: a week's tournaments are stored in group order."""
    if hasattr(tourney, 'subtype'):
        return tourney.subtype
    same_week = [t for t in all_tourneys if t.week == tourney.week]
    return get_tourney_subtype(tourney.type, same_week.index(tourney), tourney.team_list)

def get_tourney_subtype(tourney_type, group_index, group_teams):
    if tourney_type == "Division":
        return group_teams[0].division
    elif tourney_type == "Score":
        labels = ['1st/2nd', '3rd/4th', '5th/6th', '7th/8th']
        return labels[group_index]
    else:
        return None
