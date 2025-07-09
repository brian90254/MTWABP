# BRIAN COX copyright 2025

import pandas as pd
import sys

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

# === LOAD WEIGHTS ===
weights_df = pd.read_csv('CSV/indicator_weights.csv')  # Must match on 'INDICATOR'
df = df.merge(weights_df, on='INDICATOR', how='left')
df['WEIGHT'] = df['WEIGHT'].fillna(1.0)

# === CALCULATE WEIGHTED SCORE ===
df['WEIGHTED_SCORE'] = df['SCORE'] * df['WEIGHT']

# === SUM BY TEAM ===
team_scores = df.groupby('OffenseTeam')['WEIGHTED_SCORE'].sum().reset_index()
team_scores.rename(columns={'WEIGHTED_SCORE': 'FINAL_SCORE'}, inplace=True)

# === OUTPUT ===
print(team_scores)

# Optional: save to file
team_scores.to_csv('Outputs/final_weighted_team_scores.csv', index=False)
