from flask import Flask, render_template, request, session
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
import pickle
from show_results import *
from show_standings import *
from league import H2H_WEEKS, TOURNEY_TYPES, FIRST_TOURNEY_WEEK
import os

# Load all tiers data
with open("season_all_tiers.pkl", "rb") as f:
    all_tiers_data = pickle.load(f)

# Available tiers
AVAILABLE_TIERS = ['Tier 1', 'Tier 2', 'Tier 3', 'Tier 4']

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Set a proper secret key

app.config["TEMPLATES_AUTO_RELOAD"] = True

def format_full_name(name):
    """Convert 'JOHN DOE' to 'John Doe'"""
    return name.title()

def format_short_name(name):
    """Convert 'JOHN DOE' to 'J. Doe'"""
    parts = name.split()
    if len(parts) >= 2:
        return f"{parts[0][0]}. {parts[-1].title()}"
    return name.title()

app.jinja_env.filters['ordinal'] = ordinal
app.jinja_env.filters['full_name'] = format_full_name
app.jinja_env.filters['short_name'] = format_short_name

@app.before_request
def set_current_week_and_tier():
    # Get current week from session or default to 1
    if 'current_week' not in session:
        session['current_week'] = 1
    
    # Get current tier from session or default to Tier 1
    if 'current_tier' not in session:
        session['current_tier'] = 'Tier 1'
    
    # Check if week is being changed
    if request.args.get('set_week'):
        session['current_week'] = float(request.args.get('set_week'))
    
    # Check if tier is being changed
    if request.args.get('set_tier'):
        new_tier = request.args.get('set_tier')
        if new_tier in AVAILABLE_TIERS:
            session['current_tier'] = new_tier
    
    return None

@app.context_processor
def inject_globals():
    return {
        'current_week': session.get('current_week', 1),
        'current_tier': session.get('current_tier', 'Tier 1'),
        'available_tiers': AVAILABLE_TIERS
    }

def get_current_tier_data():
    """Helper function to get current tier's data"""
    tier = session.get('current_tier', 'Tier 1')
    return all_tiers_data[tier]

@app.route("/")
def index():
    current_week = session.get('current_week', 1)
    tier_data = get_current_tier_data()
    
    teams = tier_data['teams']
    schedule = tier_data['schedule']
    all_tourneys = tier_data['all_tourneys']
    
    standings_data = get_standings_by_division(teams, schedule, all_tourneys, current_week)
    playoff_standings = get_playoff_standings(teams, schedule, all_tourneys, current_week)

    return render_template("index.html", standings_data=standings_data, playoff_standings=playoff_standings)

@app.route('/team/<team_name>')
def team_page(team_name):
    current_week = session.get('current_week', 1)
    tier_data = get_current_tier_data()
    
    teams = tier_data['teams']
    schedule = tier_data['schedule']
    all_tourneys = tier_data['all_tourneys']

    # Get the team object
    team = [team for team in teams if team.team_name == team_name][0]
    
    # Check if we're in preseason (Week 0)
    if current_week == 0:
        # Preseason mode - show preview
        players = []
        for player in team.players:
            # Use initial stats (aimmax, speedmax, etc.)
            s = player.start_stats
            players.append({
                'pid': player.pid,
                'name': player.name,
                'avg_stats': 0.25*(s['Aim']+s['Speed']+s['Throw']+s['Hands']),
                'aim': s['Aim'],
                'speed': s['Speed'],
                'throw': s['Throw'],
                'hands': s['Hands'],
                'games_played': 0
            })
        
        # Get schedule preview for this team
        team_schedule = []
        
        # Get H2H matches
        for week in H2H_WEEKS:
            week_matches = [m for m in schedule if m.week == week and 
                          (m.team1.team_name == team_name or m.team2.team_name == team_name)]
            if week_matches:
                match = week_matches[0]
                opponent = match.team2.team_name if match.team1.team_name == team_name else match.team1.team_name
                home_away = "vs" if match.team1.team_name == team_name else "@"
                team_schedule.append({
                    'week': week,
                    'type': 'H2H',
                    'opponent': opponent,
                    'home_away': home_away
                })
        
        # Get tournament schedule
        for week, tourney_type in enumerate(TOURNEY_TYPES, start=FIRST_TOURNEY_WEEK):
            team_schedule.append({
                'week': week,
                'type': 'Tournament',
                'tournament_type': tourney_type,
                'opponent': None,
                'home_away': None
            })
        
        return render_template('team.html',
                             team=team,
                             players=players,
                             results_html=None,
                             is_preseason=True,
                             team_schedule=team_schedule)
    
    else:
        # Regular season mode - show results and current stats
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
                'name': player.name,
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
                             results_html=results_html,
                             is_preseason=False,
                             team_schedule=None)

@app.route("/schedule")
@app.route("/schedule/<week>")
def wkschedule(week = None):
    current_week = session.get('current_week', 16)  # "Today's date"
    tier_data = get_current_tier_data()
    
    teams = tier_data['teams']
    schedule = tier_data['schedule']
    all_tourneys = tier_data['all_tourneys']
    
    week_num = float(week) if week is not None else 1

    # Determine if results should be shown
    show_results = week_num <= current_week
    tourney_show = True if show_results else week_num not in [7, 11, 14]

    # Each team as it enters week_num, limited to what's known as of current_week:
    #   n           = number of score entries to count
    #   rating_week = which all_stats entry to use for ratings
    n, rating_week = snapshot(week_num, current_week)

    if week_num in H2H_WEEKS:
        filtered_schedule = [match for match in schedule if match.week==week_num]

        for event in filtered_schedule:
            event.schedule_index = schedule.index(event)
            event.team1_ratings = get_week_rating(event.team1, rating_week)
            event.team2_ratings = get_week_rating(event.team2, rating_week)
            event.team1_rating = sum(event.team1_ratings.values()) / 4
            event.team2_rating = sum(event.team2_ratings.values()) / 4
            event.team1_score = sum(event.team1.score[:n])
            event.team2_score = sum(event.team2.score[:n])
            event.team1_division = event.team1.division
            event.team2_division = event.team2.division
            event.team1_place = division_place(event.team1, teams, n, rating_week)
            event.team2_place = division_place(event.team2, teams, n, rating_week)
          

        return render_template('wkschedule.html', week=week_num, is_tournament=False,
                               events=filtered_schedule, show_results=show_results,
                               tourney_show=None)

    else:
        tournaments = []
        for tourney in all_tourneys:
            if tourney.week == week_num:
                # Listed best first: score, tourney wins, H2H match wins, then rating
                teams_info = []
                for team, rating in ranked(tourney.team_list, n, rating_week):
                    team_ratings = get_week_rating(team, rating_week)
                    s = team.score[:n]
                    teams_info.append({
                        'team': team.team_name,
                        'score': sum(s),
                        'division': team.division,
                        'place': division_place(team, teams, n, rating_week),
                        'ratings': team_ratings,
                        'rating': rating,
                        'FP': s.count(21),
                        'H2H': s[:4].count(15)
                    })

                tournaments.append({
                    'id': tourney.id,
                    'teams_info': teams_info
                })

        return render_template('wkschedule.html', week=week_num, is_tournament=True,
                               tournaments=tournaments, show_results=show_results,
                               tourney_show=tourney_show)

@app.route('/tournament/<int:tournament_id>')
def view_tournament(tournament_id):
    tier_data = get_current_tier_data()
    all_tourneys = tier_data['all_tourneys']
    
    tourney = all_tourneys[tournament_id]
    current_tier = session.get('current_tier', 'Tier 1')

    tournament_type = getattr(tourney, 'type', None)
    tournament_subtype = getattr(tourney, 'subtype', None)
    
    # Prepare tournament data
    teams_info = {}
    i = 1
    for team in tourney.team_list:
        
        team_ratings = get_week_rating(team,tourney.week)
        team_rating = 0.25*(team_ratings['Aim']+team_ratings['Speed']+team_ratings['Throw']+team_ratings['Hands'])
        teams_info[team.team_name] = {
                           'seed': i,
                           'score': sum(team.score[0:(tourney.week+1)]),
                           'rating': round(team_rating,1)
                          }
        i+=1
    tournament_data = {
        'week': tourney.week,
        'tier': current_tier,
        'tournament_type': tournament_type,
        'tournament_subtype': tournament_subtype,
        'tournament_id': tournament_id,
        'teams_info': teams_info,
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
    tier_data = get_current_tier_data()
    teams = tier_data['teams']
    
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
    
    # Get all stats up to current_week
    stats_history = []
    for stat in player.all_stats:
        if stat['Week'] <= current_week:
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
            })

    stats_for_week = get_player_ranks(teams,current_week)
    current_stats = [stat for stat in stats_for_week if stat['pid'] == pid]
    
    return render_template('player.html',
                         player=player,
                         team=player_team,
                         current_stats=current_stats[0],
                         stats_history=stats_history)


def render_match_animation(match, match_index, game_index, tournament_id=None):
    """Render dodgeball_animation.html for one game of a match.

    tournament_id is None for regular season matches."""
    if game_index is None:
        game_index = 0

    if not hasattr(match, 'games') or game_index >= len(match.games):
        return "Game not found", 404

    game = match.games[game_index]
    game_log = game.log if getattr(game, 'log', None) else []

    players = match.team1.players + match.team2.players
    player_names = {p.pid: p.name for p in players if getattr(p, 'name', None)}

    # Cumulative play logs across all games up to and including this one
    all_games_logs = []
    for g in match.games[:game_index + 1]:
        all_games_logs.extend(getattr(g, 'log', []))

    # Which set this game is in, and its position within that set
    current_set = 0
    game_in_set = 0
    games_counted = 0
    for set_idx, (wins1, wins2) in enumerate(match.set_results):
        if games_counted + wins1 + wins2 > game_index:
            current_set = set_idx
            game_in_set = game_index - games_counted + 1
            break
        games_counted += wins1 + wins2

    # Sets won so far (completed sets only)
    current_set_scores = [0, 0]
    for wins1, wins2 in match.set_results[:current_set]:
        current_set_scores[0 if wins1 > wins2 else 1] += 1

    # Game score within the current set BEFORE this game
    current_game_scores = [0, 0]
    set_start_game = sum(w1 + w2 for w1, w2 in match.set_results[:current_set])
    for g in match.games[set_start_game:game_index]:
        if g.winner in (1, 2):
            current_game_scores[g.winner - 1] += 1

    match_info = {
        'team1': match.team1.team_name,
        'team2': match.team2.team_name,
        'week': match.week,
        'game_number': game_index + 1,
        'total_games': len(match.games),
        'current_set': current_set + 1,
        'game_in_set': game_in_set,
        'set_scores': current_set_scores,
        'game_scores': current_game_scores,
        'is_tournament': tournament_id is not None,
        'tournament': tournament_id,
        'team1_roster': [p.pid for p in match.team1.players],
        'team2_roster': [p.pid for p in match.team2.players]
    }

    return render_template('dodgeball_animation.html',
                         game_log=game_log,
                         all_games_logs=all_games_logs,
                         match_info=match_info,
                         match_index=match_index,
                         game_index=game_index,
                         player_names=player_names)


@app.route('/animate/match/<int:match_index>')
@app.route('/animate/match/<int:match_index>/game/<int:game_index>')
def animate_match(match_index, game_index=None):
    """Animate a regular season match - shows all games in sequence"""
    schedule = get_current_tier_data()['schedule']

    if match_index >= len(schedule):
        return "Match not found", 404

    return render_match_animation(schedule[match_index], match_index, game_index)


@app.route('/animate/tournament/<int:tournament_id>/<int:match_index>')
@app.route('/animate/tournament/<int:tournament_id>/<int:match_index>/game/<int:game_index>')
def animate_tournament_match(tournament_id, match_index, game_index=None):
    all_tourneys = get_current_tier_data()['all_tourneys']

    if tournament_id >= len(all_tourneys):
        return "Tournament not found", 404

    tourney = all_tourneys[tournament_id]

    if match_index >= len(tourney.matches) or not tourney.matches[match_index]:
        return "Match not found", 404

    return render_match_animation(tourney.matches[match_index], match_index, game_index,
                                  tournament_id=tournament_id)


if __name__ == "__main__":
    app.run(debug=True)
