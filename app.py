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


@app.route("/wkschedule", methods=['GET', 'POST'])
def wkschedule():
    selected_week = request.args.get('week', default = 1., type = float)

    filtered_schedule = [match for match in schedule if match.week==selected_week]
    return render_template("wkschedule.html", events = filtered_schedule, selected_week = selected_week)

@app.route('/tournament/<int:tournament_id>')
def show_tournament(tournament_id):
    tourney = all_tourneys[tournament_id]
    
    # Prepare tournament data
    tournament_data = {
        'teams': [
            {'seed': i+1, 'name': team.team_name} 
            for i, team in enumerate(tourney.teams)
        ],
        'matches': []
    }
    
    # Add all matches in order
    for match in tourney.matches:
        if match:  # Handle case where match might be None (like GF2)
            match_data = {
                'team1_name': match.team1.team_name,
                'team2_name': match.team2.team_name,
                'team1_score': match.match_score[0],
                'team2_score': match.match_score[1],
                'winner': match.winner,  # 1 or 2
                'games': [{'winner': game.winner} for game in match.games]
            }
            tournament_data['matches'].append(match_data)
        else:
            tournament_data['matches'].append(None)
    
    return render_template('tournament.html', tournament_data=tournament_data)


if __name__ == "__main__":
    app.run(debug=True)
