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

        # === GENERATE POINT SPREADS ===
        point_spreads = []

        grouped = full_df.groupby('MATCHUP')

        for matchup, group in grouped:
            # Extract team names from matchup label
            if '_vs_' in matchup:
                team_a, team_b = matchup.split('_vs_')
            else:
                continue  # Skip if format doesn't match

            try:
                score_a = group.loc[group['OffenseTeam'] == team_a, 'FINAL_SCORE'].values[0]
                score_b = group.loc[group['OffenseTeam'] == team_b, 'FINAL_SCORE'].values[0]
                spread = round(score_a - score_b, 2)

                # Vegas line formatting
                vegas_line_value = round(abs(spread) * 2) / 2.0  # nearest 0.5
                if vegas_line_value == 0:
                    vegas_line = "PICK"
                elif spread > 0:
                    vegas_line = f"{team_a} -{vegas_line_value}"
                else:
                    vegas_line = f"{team_b} -{vegas_line_value}"

                point_spreads.append({
                    'MATCHUP': matchup,
                    'TEAM_A': team_a,
                    'TEAM_B': team_b,
                    'SCORE_A': round(score_a, 2),
                    'SCORE_B': round(score_b, 2),
                    'POINT_SPREAD (A - B)': spread,
                    'VEGAS_LINE': vegas_line
                })

            except IndexError:
                print(f"Warning: Could not find scores for both teams in {matchup}")

        spread_df = pd.DataFrame(point_spreads)
        print(spread_df)
        spread_df.to_csv('Outputs/PointSpreads.csv', index=False)

    else:
        print("No matching files found.")
