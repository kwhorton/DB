from flask import Flask, render_template, request, session
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
app.secret_key = 'your_secret_key'  # Set a proper secret key

app.config["TEMPLATES_AUTO_RELOAD"] = True

@app.before_request
def set_current_week():
    # Get current week from session or default to 16
    if 'current_week' not in session:
        session['current_week'] = 16
    
    # Check if week is being changed
    if request.args.get('set_week'):
        session['current_week'] = float(request.args.get('set_week'))
    
    # Make it available to all templates
    return None

@app.context_processor
def inject_current_week():
    return {'current_week': session.get('current_week', 16)}

@app.route("/")

def index():
    current_week = session.get('current_week', 16)
    standings_data = get_standings_by_division(teams, schedule, all_tourneys, current_week)
    return render_template("index.html", standings_data=standings_data)

@app.route('/team/<team_name>')
def team_page(team_name):
    current_week = session.get('current_week', 16)


    # Get the team object
    team = [team for team in teams if team.team_name == team_name][0]
    
    
    
    # Get results HTML using your existing function
    results_html = results(team_name, teams, schedule, all_tourneys, current_week)
    
    # Get player roster
    players = []
    for player in team.players:
        
        gp_total = 0
        for stat in player.all_stats:
            if stat['Week'] <= current_week:
                gp_total += stat['GP']

            if stat['Week'] == current_week:
                stats = [stat['Aim'],stat['Speed'],stat['Throw'],stat['Hands']]
        avg_stats = sum(stats)/len(stats)

                
        players.append({
            'pid': player.pid,
            'avg_stats': avg_stats,
            'aim': stats[0],
            'speed': stats[1],
            'throw': stats[2],
            'hands': stats[3],
            'games_played': gp_total
            })
    
    return render_template('team.html',
                         team=team,
                         players=players,
                         results_html=results_html)


#@app.route("/wkschedule", methods=['GET', 'POST'])

@app.route("/schedule")
@app.route("/schedule/<week>")

#def wkschedule():
def wkschedule(week = None):


    if week is None:
        week= 1

    #selected_week = request.args.get('week', default = 1., type = float)
    week_num = float(week)


    #if selected_week in [1, 1.5, 2, 2.5]:
    if week_num in [1, 1.5, 2, 2.5]:
        filtered_schedule = [match for match in schedule if match.week==week_num]

        for event in filtered_schedule:
            event.team1_ratings = get_week_rating(event.team1,week_num)
            event.team2_ratings = get_week_rating(event.team2,week_num)

            event.team1_rating = 0.25*(event.team1_ratings['Aim']+event.team1_ratings['Speed']+event.team1_ratings['Throw']+event.team1_ratings['Hands'])
            event.team2_rating = 0.25*(event.team2_ratings['Aim']+event.team2_ratings['Speed']+event.team2_ratings['Throw']+event.team2_ratings['Hands'])
            
            end = (week_num>=3)*(week_num+1) + (week_num<3)*(2*week_num-2) 
            end = int(end)

            event.team1_score = sum(event.team1.score[0:end])
            event.team2_score = sum(event.team2.score[0:end])

            event.team1_division = event.team1.division
            event.team2_division = event.team2.division

            division_teams_1 = [t for t in teams if t.division == event.team1.division]
            division_teams_2 = [t for t in teams if t.division == event.team2.division]
            
            # Sort by score, FP, H2H
            division_teams_1.sort(key=lambda t: (
                -sum(t.score[0:end]),
                -t.score[0:end].count(21),
                -t.score[0:min(4, end)].count(15)
            ))
            division_teams_2.sort(key=lambda t: (
                -sum(t.score[0:end]),
                -t.score[0:end].count(21),
                -t.score[0:min(4, end)].count(15)
            ))
            
            event.team1_place = [team.team_name for team in division_teams_1].index(event.team1.team_name) + 1
            event.team2_place = [team.team_name for team in division_teams_2].index(event.team2.team_name) + 1
  

            
            



        
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


@app.route('/player/<pid>')
def player_page(pid):
    current_week = session.get('current_week', 16)
    
    # Find the player
    player = None
    player_team = None
    
    for team in teams:
        for p in team.players:
            if p.pid == pid:
                player = p
                player_team = team
                break
        if player:
            break
    
    if not player:
        return "Player not found", 404
    
    # Get current stats (up to current_week)
    current_stats = {
        'aim': 0,
        'speed': 0,
        'throw': 0,
        'hands': 0
    }
    
    # Get the most recent stats up to current_week

    
    
    # Get all stats up to current_week
    stats_history = []
    for stat in player.all_stats:
        if stat['Week'] <= current_week:
            current_stats['aim'] = stat['Aim']
            current_stats['speed'] = stat['Speed']
            current_stats['throw'] = stat['Throw']
            current_stats['hands'] = stat['Hands']
            stats_history.append({
                'week': stat['Week'],
                'gp': stat['GP'],
                'throws': stat['Throws'],
                'hits': stat['Hits'],
                'blocked': stat['Blocked'],
                'caught': stat['Caught'],
                'targeted': stat['Targeted'],
                'hit': stat['Hit'],
                'blocks': stat['Blocks'],
                'catches': stat['Catches']
#                'aim': stat['Aim'],
 #               'speed': stat['Speed'],
  #              'throw': stat['Throw'],
   #             'hands': stat['Hands'],
                
    #            'avg': (stat['Aim'] + stat['Speed'] + stat['Throw'] + stat['Hands']) / 4
            })

     # Calculate average
    avg_stat = sum(current_stats.values()) / 4

   
    return render_template('player.html',
                         player=player,
                         team=player_team,
                         current_stats=current_stats,
                         avg_stat=avg_stat,
                         stats_history=stats_history)




if __name__ == "__main__":
    app.run(debug=True)
