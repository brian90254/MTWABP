# BRIAN COX copyright 2025
#
# SHORTCUT SCRIPT:
#   runSportsDataAggregator.command
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
# THEN RUN THE CODE IN "src" AND PASS ARGUMENTS "Year", "Start Week", "End Week"
#   python src/SportsDataAggregator_2.py 2024 3 4
# ----------------------------

import os
import sys
import pandas as pd
from collections import defaultdict
import argparse

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Aggregate weekly NFL team stats across a range of weeks.")
    parser.add_argument("year", type=str, help="Season year, e.g. 2024")
    parser.add_argument("start_week", type=int, help="Starting week number")
    parser.add_argument("end_week", type=int, help="Ending week number")
    args = parser.parse_args()

    base_year = args.year
    start_week = args.start_week
    end_week = args.end_week

    base_directory = 'CSV'
    output_directory = 'Aggregated'
    weeks = range(start_week, end_week + 1)
    team_stats = defaultdict(lambda: pd.DataFrame())  # team_role → full DataFrame

    # Collect data by team-role-week
    for week in weeks:
        week_dir = os.path.join(base_directory, base_year, str(week))
        if not os.path.isdir(week_dir):
            continue

        week_col = f'week_{week}'
        seen_teams = set()

        for filename in os.listdir(week_dir):
            if filename.endswith('.csv') and 'TeamStats' in filename:
                filepath = os.path.join(week_dir, filename)
                df = pd.read_csv(filepath)

                # Team names
                team1, team2 = df.columns[1], df.columns[2]
                df.set_index(df.columns[0], inplace=True)

                # Store offense and defense
                for team, opponent in [(team1, team2), (team2, team1)]:
                    for role, source in [('Offense', team), ('Defense', opponent)]:
                        key = f'{team}_{role}'
                        if key not in team_stats:
                            team_stats[key] = pd.DataFrame(index=df.index)
                        team_stats[key][week_col] = df[source]
                        seen_teams.add(key)

        # Fill in "bye" for teams not seen this week
        for key in team_stats:
            if week_col not in team_stats[key].columns:
                team_stats[key][week_col] = 'bye'

    # Ensure output directory exists
    output_path = os.path.join(base_directory, base_year, output_directory)
    os.makedirs(output_path, exist_ok=True)

    # Save to CSV
    for key, df in team_stats.items():
        df.to_csv(os.path.join(output_path, f'{key}.csv'))

    print("✅ All team stats aggregated with byes.")

if __name__ == "__main__":
    main()
