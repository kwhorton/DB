import pandas as pd
from player import *
from team import *
import pickle


def load_playerdb(pickle_file):
    """
    Load the playerdb list from a pickle file.
    
    Parameters:
    - pickle_file: Path to the pickle file containing playerdb list
    
    Returns:
    - playerdb: List of PlayerDB objects
    """
    with open(pickle_file, 'rb') as f:
        playerdb = pickle.load(f)
    return playerdb


def merge_playerdb_with_teams(teams, playerdb):
    """
    Merge PlayerDB information (name and yeargroup) into Player objects in teams.
    
    Parameters:
    - teams: List of Team objects with Player objects
    - playerdb: List of PlayerDB objects
    
    Returns:
    - teams: Updated teams list with name and yeargroup added to players
    """
    # Create a dictionary mapping player_id to PlayerDB object for quick lookup
    playerdb_dict = {pdb.player_id: pdb for pdb in playerdb}
    
    # Iterate through all teams and players
    for team in teams:
        for player in team.players:
            # Look up the player in the playerdb
            if player.pid in playerdb_dict:
                pdb = playerdb_dict[player.pid]
                # Add name and yeargroup attributes to the Player object
                player.name = pdb.name
                player.yeargroup = pdb.yeargroup
            else:
                # If player not found in playerdb, set default values
                player.name = f"Unknown ({player.pid})"
                player.yeargroup = None
                print(f"Warning: Player {player.pid} not found in playerdb")
    
    return teams


def load_teams_and_players(roster_file='roster2033.csv', teams_file='allteams2033.csv', 
                           tier='Tier 1', playerdb_file=None):
    """
    Load teams and players from CSV files, optionally merging with playerdb.
    
    Parameters:
    - roster_file: CSV file containing player data
    - teams_file: CSV file containing team metadata
    - tier: Filter teams by tier (default: 'Tier 1')
    - playerdb_file: Optional path to pickle file containing playerdb
    
    Returns:
    - teams: List of Team objects with their players
    """
    
    # Load the CSV files
    roster_df = pd.read_csv(roster_file)
    teams_df = pd.read_csv(teams_file)
    
    # Filter for specified tier
    teams_df = teams_df[teams_df['Level'] == tier]
    
    # Create a dictionary to store teams
    teams = []
    
    # Iterate through each team in the teams dataframe
    for _, team_row in teams_df.iterrows():
        team_name = team_row['Team']
        division = team_row['Division']
        
        # Get all players for this team from the roster
        team_players_df = roster_df[roster_df['Team'] == team_name]
        
        # Create Player objects for each player on the team
        players = []
        for _, player_row in team_players_df.iterrows():
            player = Player(
                pid=player_row['Name'],
                aim=player_row['Aim'],
                speed=player_row['Speed'],
                throw=player_row['Throw'],
                hands=player_row['Hands']
            )
            players.append(player)
        
        # Create the Team object
        team = Team(
            team_name=team_name,
            division=division,
            players=players
        )
        
        # Calculate team rating
        team.get_team_rating()
        
        teams.append(team)
    
    # If playerdb file is provided, merge the data
    if playerdb_file:
        playerdb = load_playerdb(playerdb_file)
        teams = merge_playerdb_with_teams(teams, playerdb)
    
    return teams


def load_all_tiers(roster_file='roster2033.csv', teams_file='allteams2033.csv', playerdb_file=None):
    """
    Load all 4 tiers of teams.
    
    Returns:
    - Dictionary with tier names as keys and team lists as values
    """
    tiers = {}
    for tier_num in range(1, 5):
        tier_name = f"Tier {tier_num}"
        print(f"Loading {tier_name}...")
        tiers[tier_name] = load_teams_and_players(
            roster_file=roster_file,
            teams_file=teams_file,
            tier=tier_name,
            playerdb_file=playerdb_file
        )
        print(f"  Loaded {len(tiers[tier_name])} teams")
    return tiers


# Load only Tier 1 by default for backward compatibility
teams = load_teams_and_players(playerdb_file = "player_db.pkl")

# Load all tiers
all_tiers = load_all_tiers(playerdb_file = "player_db.pkl")
