import pandas as pd
from bs4 import BeautifulSoup
import requests
import argparse
import os

def get_weekly_team_stats(season_year, week):
    url = f"https://www.pro-football-reference.com/years/{season_year}/week_{week}.htm"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Error fetching week {week} data for {season_year}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    games = soup.find_all('div', class_='game_summary expanded nohover')

    matchups = []

    for game in games:
        links = game.find_all('a')
        box_link = next((a['href'] for a in links if 'boxscores' in a['href']), None)
        if not box_link:
            continue

        boxscore_url = f"https://www.pro-football-reference.com{box_link}"
        try:
            box = pd.read_html(boxscore_url)
        except Exception as e:
            print(f"Error parsing boxscore for {boxscore_url}: {e}")
            continue

        # === DEBUG OPTION: Dump table preview ===
        # for i, tbl in enumerate(box):
        #     print(f"\nTable {i} preview:\n", tbl.head())

        # Find team summary table
        team_summary = None
        for tbl in box:
            if tbl.shape[1] >= 3 and 'Time of Possession' in tbl.iloc[:, 0].values:
                team_summary = tbl
                break

        if team_summary is None:
            print(f"⚠️ Team summary not found for {boxscore_url}")
            continue

        home_col = team_summary.columns[2]
        away_col = team_summary.columns[1]

        try:
            # Rows to extract
            rush_row = team_summary[team_summary.iloc[:, 0] == 'Rush-Yds-TDs']
            pass_row = team_summary[team_summary.iloc[:, 0] == 'Cmp-Att-Yd-TD-INT']
            fumble_row = team_summary[team_summary.iloc[:, 0] == 'Fumbles-Lost']
            penalty_row = team_summary[team_summary.iloc[:, 0] == 'Penalties-Yards']
            poss_row = team_summary[team_summary.iloc[:, 0] == 'Time of Possession']

            # Scores from summary section
            team_names = [td.get_text() for td in game.find_all('td', class_='team')]
            scores = [int(td.get_text()) for td in game.find_all('td', class_='right') if td.get_text().isdigit()]
            if len(team_names) != 2 or len(scores) < 2:
                print(f"⚠️ Skipping malformed score table in {boxscore_url}")
                continue

            away_team_name = team_names[0]
            home_team_name = team_names[1]
            away_pts = scores[0]
            home_pts = scores[1]

            # Helper parsers
            def get_rush_yds(val): return int(val.split('-')[1])
            def get_pass_yds(val): return int(val.split('-')[2])
            def get_ints(val): return int(val.split('-')[4])
            def get_fumbles_lost(val): return int(val.split('-')[1])
            def get_penalty_yds(val): return int(val.split('-')[1])

            matchups.append({
                'Home Team': home_col,
                'Home Points': home_pts,
                'Home Rushing Yards': get_rush_yds(rush_row[home_col].values[0]),
                'Home Passing Yards': get_pass_yds(pass_row[home_col].values[0]),
                'Home Time of Possession': poss_row[home_col].values[0],
                'Home Penalty Yards': get_penalty_yds(penalty_row[home_col].values[0]),
                'Home Fumbles Lost': get_fumbles_lost(fumble_row[home_col].values[0]),
                'Home INTs': get_ints(pass_row[home_col].values[0]),

                'Away Team': away_col,
                'Away Points': away_pts,
                'Away Rushing Yards': get_rush_yds(rush_row[away_col].values[0]),
                'Away Passing Yards': get_pass_yds(pass_row[away_col].values[0]),
                'Away Time of Possession': poss_row[away_col].values[0],
                'Away Penalty Yards': get_penalty_yds(penalty_row[away_col].values[0]),
                'Away Fumbles Lost': get_fumbles_lost(fumble_row[away_col].values[0]),
                'Away INTs': get_ints(pass_row[away_col].values[0])
            })

            print(f"✓ Parsed game: {home_col} vs {away_col}")

        except Exception as e:
            print(f"Stat parsing error for {boxscore_url}: {e}")
            continue

    if not matchups:
        print("⚠️ No valid matchups were parsed.")
        return None

    return pd.DataFrame(matchups)


def main():
    parser = argparse.ArgumentParser(description="Download NFL weekly stats with turnovers and possession.")
    parser.add_argument("season_year", type=int, help="NFL season year (e.g., 2023)")
    parser.add_argument("week", type=int, help="Week number (1–18 for regular season)")

    args = parser.parse_args()
    stats_df = get_weekly_team_stats(args.season_year, args.week)

    if stats_df is not None and not stats_df.empty:
        output_dir = "CSV"
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{output_dir}/NFL_Stats_{args.season_year}_Week_{args.week}.csv"
        stats_df.to_csv(filename, index=False)
        print(f"\n✅ Saved stats to: {filename}")
    else:
        print("\n🚫 No data was returned.")

if __name__ == "__main__":
    main()
