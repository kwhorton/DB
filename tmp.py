import pandas as pd
from player import *
from team import *
import pickle


with open("player_db.pkl", 'rb') as f:
    playerdb = pickle.load(f)
