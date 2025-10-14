from flask import Flask, render_template, request
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
import pickle
from show_standings import *
from show_results import *
import os

with open("season.pkl","rb") as f:
    teams = pickle.load(f)
    schedule = pickle.load(f)
    all_tourneys = pickle.load(f)

for idx, tourney in enumerate(all_tourneys):
    tourney.id = idx
        
app = Flask(__name__)

app.config["TEMPLATES_AUTO_RELOAD"] = True

@app.route("/")

def index():
    standings_html = standings(teams,schedule,all_tourneys,16)
    return render_template("index.html", table=standings_html)

@app.route("/team_name/<team_name>")
def team_results(team_name):
    results_html = results(team_name,teams,schedule,all_tourneys,16)
    return render_template("team_results.html",team_name=team_name, table = results_html)


#@app.route("/wkschedule", methods=['GET', 'POST'])

@app.route("/schedule")
@app.route("/schedule/<week>")

#def wkschedule():
def wkschedule(week = None):
    if week is None:
        week= '1'

    #selected_week = request.args.get('week', default = 1., type = float)
    week_num = float(week)
    
    #if selected_week in [1, 1.5, 2, 2.5]:
    if week_num in [1, 1.5, 2, 2.5]:
        filtered_schedule = [match for match in schedule if match.week==week_num]
        #return render_template("wkschedule.html", events = filtered_schedule, selected_week = selected_week)
        return render_template('wkschedule.html', week = week_num, is_tournament = False, events = filtered_schedule)


    else:
        tournaments = []
        for tourney in all_tourneys:
            if tourney.week == week_num:
                tourney_info = {
                    'id': tourney.id,  # Use the actual ID
                    'teams': [team.team_name for team in tourney.team_list]
                }
                tournaments.append(tourney_info)
        return render_template('wkschedule.html', week= week_num, is_tournament = True, tournaments = tournaments)


@app.route('/tournament/<int:tournament_id>')
def view_tournament(tournament_id):

    tourney = all_tourneys[tournament_id]
    # Prepare tournament data
    tournament_data = {
        'week': tourney.week,
        'teams': [
            {'seed': i+1, 'name': team.team_name} 
            for i, team in enumerate(tourney.team_list)
        ],
        'matches': []
    }
    
    for match in tourney.matches:
        if match:
            match_data = {
                'team1_name': match.team1.team_name,
                'team2_name': match.team2.team_name,
                'team1_score': match.match_score[0],
                'team2_score': match.match_score[1],
                'winner': match.winner,
                'games': [{'winner': game.winner} for game in match.games]
            }
            tournament_data['matches'].append(match_data)
        else:
            tournament_data['matches'].append(None)
    
    return render_template('tournament.html', tournament_data=tournament_data)



if __name__ == "__main__":
    app.run(debug=True)
