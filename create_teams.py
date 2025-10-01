import random
from player import *
from team import *


teams = []
divs = ['East', 'Midwest', 'South', 'West']
for d in range(4):
    for j in range(1,9):
        team_id = f"T{8*d+j:03}"
        team_mean = random.randint(300,400)
        players = []
        for i in range(1,9):
            player_id = f"P{8*(j-1)+i:03}"
            player_aim = random.randint(team_mean-20,team_mean+20)
            player_speed = random.randint(team_mean-20,team_mean+20)
            player_throw = random.randint(team_mean-20,team_mean+20)
            player_hands = random.randint(team_mean-20,team_mean+20)
            player = Player(player_id,player_aim,player_speed,player_throw,player_hands)
            players.append(player)
        team = Team(team_id,divs[d],players)
        team.get_team_rating()
        teams.append(team)
