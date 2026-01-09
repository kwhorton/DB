# -*- coding: utf-8 -*-
"""
Created on Thu Oct  3 14:47:24 2024

@author: kwhor
"""

import pandas as pd
import random
import json

last_names = pd.read_excel('Names.xlsx',sheet_name = "Sheet1")

first_names_m = pd.read_excel('Names.xlsx',sheet_name = "Sheet2")

first_names_f = pd.read_excel('Names.xlsx',sheet_name = "Sheet3")


names = []

for i in range(1024):
    ln = random.choices(last_names['Name'],weights = last_names['Prob'])
    
    if random.random()<0.75:
        fn = random.choices(first_names_m['Name'],weights = first_names_m['Prob'])
        
    else:
        fn = random.choices(first_names_f['Name'],weights = first_names_f['Prob'])
        
    names.append(f"{fn[0]} {ln[0]}")


with open("names_data.json", 'w', encoding='utf-8') as f:
        json.dump(names, f, indent=2)
