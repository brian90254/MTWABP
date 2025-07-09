# BRIAN COX copyright 2025
#
# EXAMPLE TO RUN THIS SCRIPT:
# ---------------------------
# IN TERMINAL, NAVIGATE TO THE PROJECT FOLDER
#   cd Dropbox/GitHub/MTWABP/Tools/SOFTWARE/PythonScripts/SportsDataScraper/
# IF NEEDED, COMMAND TO MAKE A VENV:
#   python3.9 -m venv venv39
# ACTIVATE THE VENV:
#   source venv39/bin/activate
# IF NEEDED, COMMAND TO DOWNLOAD ALL REQS FOR THIS PROJECT:
#   pip3 install -r requirements.txt
# THEN RUN THE CODE IN "src" AND PASS ARGUMENTS FROM "Outputs":
#   python src/SportsDataPredictor_1.py
# ----------------------------

import pandas as pd
import sys
from collections import defaultdict

# === CONFIGURATION ===
CSV_FILE = sys.argv[1] if len(sys.argv) > 1 else 'input.csv'

# === LOAD DATA ===
df = pd.read_csv(CSV_FILE, sep=None, engine='python')  # auto-detect delimiter

# === EXTRACT OFFENSIVE TEAM ===
def extract_offense_team(matchup):
    parts = matchup.split(' x ')
    for part in parts:
        if 'Offense' in part:
            return part.split('_')[0]
    return None

df['OffenseTeam'] = df['MATCHUP'].apply(extract_offense_team)

# === PLACEHOLDER: ADD WEIGHTS (currently all = 1) ===
# df['WEIGHT'] = 1.0  # You can replace this later with actual weight logic

# === LOAD WEIGHTS ===
weights_df = pd.read_csv('CSV/indicator_weights.csv')  # Must match on 'INDICATOR'
df = df.merge(weights_df, on='INDICATOR', how='left')

# Fill missing weights with 1.0 as default
df['WEIGHT'] = df['WEIGHT'].fillna(1.0)


# === GROUP AND WEIGHTED AVERAGE ===
results = []

grouped = df.groupby(['INDICATOR', 'OffenseTeam'])

for (indicator, team), group in grouped:
    total_weight = group['WEIGHT'].sum()
    weighted_sum = (group['SCORE'] * group['WEIGHT']).sum()
    weighted_avg = weighted_sum / total_weight if total_weight else 0.0

    results.append({
        'INDICATOR': indicator,
        'TEAM': team,
        'WEIGHTED_AVG_SCORE': round(weighted_avg, 2)
    })

# === OUTPUT RESULTS ===
output_df = pd.DataFrame(results)
print(output_df)

# Optional: save to file
output_df.to_csv('Outputs/offense_weighted_averages.csv', index=False)
