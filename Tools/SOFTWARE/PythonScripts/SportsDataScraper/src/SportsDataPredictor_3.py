# BRIAN COX copyright 2025

import pandas as pd
import sys
import os
import glob

# === FUNCTIONS ===

def extract_offense_team(matchup):
    parts = matchup.split(' x ')
    for part in parts:
        if 'Offense' in part:
            return part.split('_')[0]
    return None

def process_file(csv_file):
    df = pd.read_csv(csv_file, sep=None, engine='python')
    df['OffenseTeam'] = df['MATCHUP'].apply(extract_offense_team)

    # Merge in indicator weights
    weights_df = pd.read_csv('CSV/indicator_weights.csv')
    df = df.merge(weights_df, on='INDICATOR', how='left')
    df['WEIGHT'] = df['WEIGHT'].fillna(1.0)

    # Compute weighted score
    df['WEIGHTED_SCORE'] = df['SCORE'] * df['WEIGHT']

    # Sum by offense team
    team_scores = df.groupby('OffenseTeam')['WEIGHTED_SCORE'].sum().reset_index()
    team_scores.rename(columns={'WEIGHTED_SCORE': 'FINAL_SCORE'}, inplace=True)

    # Add matchup label from filename
    base = os.path.basename(csv_file)
    matchup_name = base.replace('Centroid_Results_', '').replace('.csv', '')
    team_scores.insert(0, 'MATCHUP', matchup_name)

    return team_scores


# === MAIN ENTRY POINT ===

if len(sys.argv) > 1:
    # Single file mode
    input_file = sys.argv[1]
    results_df = process_file(input_file)
    print(results_df)
    results_df.to_csv('Outputs/final_weighted_team_scores.csv', index=False)
else:
    # Batch mode
    pattern = 'Outputs/Centroid_Results_*_vs_*.csv'
    files = glob.glob(pattern)

    all_results = []

    for file in files:
        print(f"Processing: {file}")
        scores_df = process_file(file)
        all_results.append(scores_df)

    if all_results:
        full_df = pd.concat(all_results, ignore_index=True)
        print(full_df)
        full_df.to_csv('Outputs/final_weighted_team_scores_ALL.csv', index=False)
    else:
        print("No matching files found.")
