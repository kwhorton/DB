from player import *
from team import *
from match import *
from tourney import *
from create_teams import *
from build_schedule import *
import random
import pandas as pd
import pickle


# Dictionary to store all data by tier
all_tiers_data = {}

# List of tier names
tier_names = ['Tier 1', 'Tier 2', 'Tier 3', 'Tier 4']

for tier_name in tier_names:
    print(f"\n{'='*60}")
    print(f"Processing {tier_name}")
    print(f"{'='*60}")
    
    # Get teams for this tier
    teams = all_tiers[tier_name]
    print(f"Teams loaded: {len(teams)}")
    
    # Build schedule for this tier
    schedule = build_h2h_schedule(teams, year=2033)
    print(f"Schedule built: {len(schedule)} head-to-head matches")
    
    # Run head-to-head matches for weeks 1, 1.5, 2, 2.5
    for week in [1, 1.5, 2, 2.5]:
        print(f"  Running Week {week} matches...")
        schedule1 = [match1 for match1 in schedule if match1.week == week]
        for match1 in schedule1:
            match1.run_match()
        update_players(teams, schedule, week)
    
    # Initialize tournament list
    all_tourneys = []
    
    # Tournament types for weeks 3-16
    tourney_types = ['Random', 'Random', 'Division', 'Division', 'Score', 'Random',
                     'Division', 'Division', 'Score', 'Random', 'Random', 'Score', 
                     'Division', 'Division']
    
    # Run tournaments for weeks 3-16
    for w in range(14):
        week_num = w + 3
        print(f"  Running Week {week_num} tournaments ({tourney_types[w]})...")
        
        teams_lists = get_tourney_list(teams, tourney_types[w])
        
        for i in range(4):
            tourney = Tournament(teams_lists[i], 2033, week_num)
            tourney.type = tourney_types[w]
            tourney.run_tourney()
            all_tourneys.append(tourney)
            schedule.extend(tourney.matches)
        
        update_players(teams, schedule, week_num)
    
    print(f"  Total tournaments: {len(all_tourneys)}")
    print(f"  Total matches (H2H + Tournament): {len(schedule)}")
    
    # Assign IDs to tournaments
    for idx, tourney in enumerate(all_tourneys):
        tourney.id = idx
    
    # Store this tier's data
    all_tiers_data[tier_name] = {
        'teams': teams,
        'schedule': schedule,
        'all_tourneys': all_tourneys
    }

# Save all data to pickle file
print(f"\n{'='*60}")
print("Saving all tiers to season_all_tiers.pkl...")
print(f"{'='*60}")

with open('season_all_tiers.pkl', 'wb') as file:
    pickle.dump(all_tiers_data, file)

print("All tiers saved successfully!")
print(f"Total tiers: {len(all_tiers_data)}")
for tier_name, data in all_tiers_data.items():
    print(f"  {tier_name}: {len(data['teams'])} teams, {len(data['schedule'])} matches, {len(data['all_tourneys'])} tournaments")

# Also save Tier 1 separately for backward compatibility
print("\nSaving Tier 1 to season.pkl for backward compatibility...")
tier1_data = all_tiers_data['Tier 1']
with open('season.pkl', 'wb') as file:
    pickle.dump(tier1_data['teams'], file)
    pickle.dump(tier1_data['schedule'], file)
    pickle.dump(tier1_data['all_tourneys'], file)
print("Tier 1 saved to season.pkl")
