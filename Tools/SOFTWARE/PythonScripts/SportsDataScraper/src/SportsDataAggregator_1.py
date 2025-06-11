import os
import pandas as pd
from collections import defaultdict

# Setup
base_directory = 'CSV'
output_directory = 'Aggregated'
base_year = '2024'
weeks = range(1, 7)
team_stats = defaultdict(lambda: pd.DataFrame())  # team_role → full DataFrame

# Collect data by team-role-week
for week in weeks:
    #week_dir = os.path.join(base_year, str(week))
    week_dir = os.path.join(base_directory, base_year, str(week))
    if not os.path.isdir(week_dir):
        continue

    week_col = f'week_{week}'
    seen_teams = set()

    for filename in os.listdir(week_dir):
        if filename.endswith('.csv'):
            filepath = os.path.join(week_dir, filename)
            df = pd.read_csv(filepath)

            # Team names
            team1, team2 = df.columns[1], df.columns[2]
            df.set_index(df.columns[0], inplace=True)

            # Store offense and defense
            for team, opponent in [(team1, team2), (team2, team1)]:
                for role, source in [('Offense', team), ('Defense', opponent)]:
                    key = f'{team}_{role}'
                    # Create column for this week
                    if key not in team_stats:
                        team_stats[key] = pd.DataFrame(index=df.index)
                    team_stats[key][week_col] = df[source]
                    seen_teams.add(key)

    # Fill in "bye" for teams not seen this week
    for key in team_stats:
        if f'week_{week}' not in team_stats[key].columns:
            team_stats[key][week_col] = 'bye'

# Save to CSV
for key, df in team_stats.items():
    #df.to_csv(os.path.join(base_year, f'{key}.csv'))
    df.to_csv(os.path.join(base_directory, base_year, output_directory, f'{key}.csv'))
print("All team stats aggregated with byes.")
