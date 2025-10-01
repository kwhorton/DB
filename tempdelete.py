import pickle

with open("season.pkl","rb") as f:
    teams = pickle.load(f)
    schedule = pickle.load(f)
    all_tourneys = pickle.load(f)
