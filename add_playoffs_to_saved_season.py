"""Play the playoffs for a season saved before main.py ran them, keeping its
regular season as is. Tiers that already have playoffs are left alone."""
import pickle
from player import *
from playoffs import run_playoffs
from tourney import backfill_game_records

with open('season_all_tiers.pkl', 'rb') as file:
    all_tiers_data = pickle.load(file)

for tier_name, data in all_tiers_data.items():
    if 'playoff_rounds' in data:
        print(f"{tier_name}: already has playoffs")
        continue
    backfill_game_records(data['teams'], data['schedule'], data['all_tourneys'])
    year = data['schedule'][0].year
    data['playoff_seeds'], data['playoff_rounds'] = run_playoffs(data['teams'], year)
    print(f"{tier_name}: champion {data['playoff_rounds'][-1].finish_order[0].team_name}")

with open('season_all_tiers.pkl', 'wb') as file:
    pickle.dump(all_tiers_data, file)
