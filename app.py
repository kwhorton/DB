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

if __name__ == "__main__":
    app.run(debug=True)
