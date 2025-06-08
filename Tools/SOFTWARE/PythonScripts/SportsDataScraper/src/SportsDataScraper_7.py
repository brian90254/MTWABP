import requests
from bs4 import BeautifulSoup, Comment
import pandas as pd
import argparse
import os

def get_boxscore_links(year, week):
    url = f"https://www.pro-football-reference.com/years/{year}/week_{week}.htm"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Failed to load week page: {url}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    links = soup.find_all('a', href=True)
    boxscore_links = [
        "https://www.pro-football-reference.com" + link['href']
        for link in links if link['href'].startswith("/boxscores/") and link['href'].endswith(".htm")
    ]
    return list(set(boxscore_links))

def extract_linescore_scores(soup):
    """Extract final team scores from the linescore table (inside HTML comments)."""
    scores = {}
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    for comment in comments:
        if 'linescore' in comment:
            try:
                comment_soup = BeautifulSoup(comment, 'html.parser')
                table = comment_soup.find('table', {'id': 'linescore'})
                if table:
                    df = pd.read_html(str(table))[0]
                    for _, row in df.iterrows():
                        team = row['Tm']
                        if 'Final' in row:
                            scores[team] = int(row['Final'])
                        elif 'T' in row:  # fallback
                            scores[team] = int(row['T'])
            except Exception as e:
                print(f"Error parsing linescore: {e}")
    return scores

def extract_team_stats_and_scores(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to retrieve: {url}")
        return None, None, None

    soup = BeautifulSoup(response.content, 'html.parser')
    game_id = url.strip('/').split('/')[-1].replace('.htm', '')

    # Extract scores from linescore
    scores = extract_linescore_scores(soup)

    # Extract Team Stats from comments
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    for comment in comments:
        if 'Team Stats' in comment:
            try:
                comment_soup = BeautifulSoup(comment, 'html.parser')
                table = comment_soup.find('table')
                if table:
                    df = pd.read_html(str(table))[0]
                    df.columns.values[0] = "Stat"
                    return df, game_id, scores
            except Exception as e:
                print(f"Error parsing stats for {url}: {e}")
                continue

    print(f"⚠️ Team Stats table not found in: {url}")
    return None, None, None

def normalize_team_stats(df, game_id, scores):
    if df is None or df.empty:
        return None

    teams = list(df.columns[1:])
    normalized_rows = []

    for team in teams:
        team_data = {'Team': team, 'Game ID': game_id}
        team_data['Points'] = scores.get(team, None)
        for _, row in df.iterrows():
            stat_type = row['Stat']
            values = str(row[team]).split('-')
            if stat_type == 'Rush-Yds-TDs' and len(values) == 3:
                team_data['Rush'] = int(values[0])
                team_data['Rush Yds'] = int(values[1])
                team_data['Rush TDs'] = int(values[2])
            elif stat_type == 'Cmp-Att-Yd-TD-INT' and len(values) == 5:
                team_data['Pass Comp'] = int(values[0])
                team_data['Pass Att'] = int(values[1])
                team_data['Pass Yds'] = int(values[2])
                team_data['Pass TD'] = int(values[3])
                team_data['INT'] = int(values[4])
            elif stat_type == 'Fumbles-Lost' and len(values) == 2:
                team_data['Fumbles'] = int(values[0])
                team_data['Fumbles Lost'] = int(values[1])
            elif stat_type == 'Penalties-Yards' and len(values) == 2:
                team_data['Penalties'] = int(values[0])
                team_data['Penalty Yds'] = int(values[1])
            elif stat_type == 'Time of Possession':
                team_data['Time of Possession'] = row[team]
            else:
                team_data[stat_type] = row[team]
        normalized_rows.append(team_data)

    return pd.DataFrame(normalized_rows)

def process_week(year, week):
    boxscore_urls = get_boxscore_links(year, week)
    output_dir = os.path.join("CSV", str(year), str(week))
    os.makedirs(output_dir, exist_ok=True)

    for url in boxscore_urls:
        print(f"🔍 Processing: {url}")
        df, game_id, scores = extract_team_stats_and_scores(url)
        norm_df = normalize_team_stats(df, game_id, scores)
        if norm_df is not None:
            filename = os.path.join(output_dir, f"{game_id}_TeamStats.csv")
            norm_df.to_csv(filename, index=False)
            print(f"✅ Saved normalized stats with points to: {filename}")

def main():
    parser = argparse.ArgumentParser(description="Normalize NFL 'Team Stats' and include points scored from linescore.")
    parser.add_argument("year", type=int, help="NFL season year (e.g., 2023)")
    parser.add_argument("week", type=int, help="Week number (1–18)")
    args = parser.parse_args()
    process_week(args.year, args.week)

if __name__ == "__main__":
    main()
