# BRIAN COX copyright 2025
#
# SHORTCUT SCRIPT:
#   runSportsDataScraper.command
#
# EXAMPLE TO RUN THIS SCRIPT:
# ---------------------------
# IN TERMINAL, NAVIGATE TO THE PROJECT FOLDER
# IF NEEDED, COMMAND TO MAKE A VENV:
#   python3.9 -m venv venv39
# ACTIVATE THE VENV:
#   source venv39/bin/activate
# IF NEEDED, COMMAND TO DOWNLOAD ALL REQS FOR THIS PROJECT:
#   pip3 install -r requirements.txt
# THEN RUN THE CODE IN "src" AND PASS ARGUMENTS "Year" and "Week"
#   python src/SportsDataScraper_11.py 2024 7
# ----------------------------

import requests
from bs4 import BeautifulSoup, Comment
import pandas as pd
import argparse
import os
import time
import random
from io import StringIO
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- Setup session with retry, proxy support, and header rotation ---
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/114.0'
]

PROXIES = [
    None,  # Add proxy strings like 'http://user:pass@proxy_ip:proxy_port' if needed
]

def create_session():
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update({
        'User-Agent': random.choice(USER_AGENTS),
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.google.com'
    })
    session.cookies.clear()
    return session

def get_boxscore_links(year, week):
    url = f"https://www.pro-football-reference.com/years/{year}/week_{week}.htm"
    session = create_session()
    response = session.get(url, proxies={'http': random.choice(PROXIES), 'https': random.choice(PROXIES)})
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

def get_weekly_game_scores(year, week):
    url = "https://www.pro-football-reference.com/boxscores/game-scores.htm"
    session = create_session()
    response = session.get(url, proxies={'http': random.choice(PROXIES), 'https': random.choice(PROXIES)})
    if response.status_code != 200:
        print(f"Failed to load game scores summary page.")
        return {}

    soup = BeautifulSoup(response.content, 'html.parser')
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    scores = {}
    for comment in comments:
        if 'games' in comment:
            try:
                comment_soup = BeautifulSoup(comment, 'html.parser')
                table = comment_soup.find('table', {'id': 'games'})
                df = pd.read_html(StringIO(str(table)))[0]
                df = df[(df['Year'] == year) & (df['Week'] == week)]
                for _, row in df.iterrows():
                    game_id = row['Boxscore'].split('/')[-1].replace('.htm', '')
                    scores[game_id] = {
                        row['Winner/tie']: row['PtsW'],
                        row['Loser/tie']: row['PtsL']
                    }
            except Exception as e:
                print(f"Error parsing weekly game scores: {e}")
    return scores

def extract_vegas_line(soup):
    info_div = soup.find('div', {'id': 'game_info'})
    if not info_div:
        return None
    lines = info_div.get_text(separator='\n').split('\n')
    for line in lines:
        if 'Vegas Line' in line:
            return line.split('Vegas Line:')[-1].strip()
    return None

def extract_team_stats(url):
    session = create_session()
    response = session.get(url, proxies={'http': random.choice(PROXIES), 'https': random.choice(PROXIES)})
    if response.status_code != 200:
        print(f"Failed to retrieve: {url}")
        return None, None, None

    soup = BeautifulSoup(response.content, 'html.parser')
    game_id = url.strip('/').split('/')[-1].replace('.htm', '')
    vegas_line = extract_vegas_line(soup)

    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    for comment in comments:
        if 'Team Stats' in comment:
            try:
                comment_soup = BeautifulSoup(comment, 'html.parser')
                table = comment_soup.find('table')
                if table:
                    df = pd.read_html(StringIO(str(table)))[0]
                    df.columns.values[0] = "Stat"
                    return df, game_id, vegas_line
            except Exception as e:
                print(f"Error parsing stats for {url}: {e}")

    print(f"⚠️ Team Stats table not found in: {url}")
    return None, None, vegas_line

def normalize_team_stats(df, game_id, scores):
    if df is None or df.empty:
        return None

    teams = list(df.columns[1:])
    normalized = {}

    for team in teams:
        team_data = {}
        team_data['Points'] = scores.get(game_id, {}).get(team)
        for _, row in df.iterrows():
            stat_type = row['Stat']
            values = str(row[team]).split('-')
            if stat_type == 'Rush-Yds-TDs' and len(values) == 3:
                team_data['Rush Att'] = int(values[0])
                team_data['Rush Yds'] = int(values[1])
                team_data['Rush TDs'] = int(values[2])
            elif stat_type == 'Cmp-Att-Yd-TD-INT' and len(values) == 5:
                team_data['Pass Comp'] = int(values[0])
                team_data['Pass Att'] = int(values[1])
                team_data['Pass Yds'] = int(values[2])
                team_data['Pass TD'] = int(values[3])
                team_data['Pass INT'] = int(values[4])
            elif stat_type == 'Sacked-Yards' and len(values) == 2:
                team_data['Sacks Taken'] = int(values[0])
                team_data['Sacked Yards'] = int(values[1])
            elif stat_type == 'Fumbles-Lost' and len(values) == 2:
                team_data['Fumbles'] = int(values[0])
                team_data['Fumbles Lost'] = int(values[1])
            elif stat_type == 'Penalties-Yards' and len(values) == 2:
                team_data['Penalties'] = int(values[0])
                team_data['Penalty Yds'] = int(values[1])
            elif stat_type == 'Third Down Conv.' and len(values) == 2:
                team_data['3D Conv'] = int(values[0])
                team_data['3D Conv Yards'] = int(values[1])
            elif stat_type == 'Fourth Down Conv.' and len(values) == 2:
                team_data['4D Conv'] = int(values[0])
                team_data['4D Conv Yards'] = int(values[1])
            elif stat_type == 'Time of Possession':
                team_data['Time of Possession'] = row[team]
            else:
                team_data[stat_type] = row[team]
        normalized[team] = team_data

    df_normalized = pd.DataFrame(normalized)
    return df_normalized

def process_week(year, week):
    game_scores = get_weekly_game_scores(year, week)
    boxscore_urls = get_boxscore_links(year, week)
    output_dir = os.path.join("CSV", str(year), str(week))
    os.makedirs(output_dir, exist_ok=True)

    for url in boxscore_urls:
        print(f"🔍 Processing: {url}")
        time.sleep(random.uniform(3.0, 6.0))  # Conservative delay
        df, game_id, vegas_line = extract_team_stats(url)
        norm_df = normalize_team_stats(df, game_id, game_scores)
        if norm_df is not None:
            filename = os.path.join(output_dir, f"{game_id}_TeamStats.csv")
            norm_df.to_csv(filename)
            print(f"✅ Saved rotated stats with points to: {filename}")
            if vegas_line:
                print(f"📈 Vegas Line: {vegas_line}")
                vegas_path = os.path.join(output_dir, f"{game_id}_vegas_line.txt")
                with open(vegas_path, 'w') as f:
                    f.write(vegas_line + '\n')

def main():
    parser = argparse.ArgumentParser(description="Rotated NFL 'Team Stats' with points scored and Vegas line.")
    parser.add_argument("year", type=int, help="NFL season year (e.g., 2023)")
    parser.add_argument("week", type=int, help="Week number (1–18)")
    args = parser.parse_args()
    process_week(args.year, args.week)

if __name__ == "__main__":
    main()
