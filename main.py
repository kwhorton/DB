from player import *
from team import *
from match import *
from tourney import *
from create_teams import *
from build_schedule import *
import random
import pandas as pd
import pickle



all_tourneys = []


schedule = build_h2h_schedule(teams,year = 2033)
for week in [1,1.5,2,2.5]:
    schedule1 = [match1 for match1 in schedule if match1.week==week]
    for match1 in schedule1:
        match1.run_match()
    update_players(teams,schedule,week)

tourney_types = ['Random','Random','Division','Division','Score','Random',
                 'Division','Division','Score','Random','Random','Score','Division',
                 'Division']

for w in range(14):
    
    teams_lists = get_tourney_list(teams,tourney_types[w])

    for i in range(4):
        tourney = Tournament(teams_lists[i],2033,w+3)
        tourney.run_tourney()
        all_tourneys.append(tourney)
        schedule.extend(tourney.matches)
    
    update_players(teams,schedule,w+3)


with open('season.pkl','wb') as file:
    pickle.dump(teams, file)
    pickle.dump(schedule, file)
    pickle.dump(all_tourneys, file)
    

