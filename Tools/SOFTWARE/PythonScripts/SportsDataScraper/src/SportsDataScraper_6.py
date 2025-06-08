import requests
from bs4 import BeautifulSoup, Comment
import pandas as pd
import argparse
import os

def get_boxscore_links(year, week):
    """Fetch all boxscore URLs for a given year and week."""
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
    return list(set(boxscore_links))  # remove duplicates

def extract_team_stats(url):
    """Extract the Team Stats table from a given boxscore URL."""
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to retrieve: {url}")
        return None, None

    soup = BeautifulSoup(response.content, 'html.parser')
    game_id = url.strip('/').split('/')[-1].replace('.htm', '')

    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    for comment in comments:
        if 'Team Stats' in comment:
            try:
                comment_soup = BeautifulSoup(comment, 'html.parser')
                table = comment_soup.find('table')
                if table:
                    df = pd.read_html(str(table))[0]
                    df['Game ID'] = game_id
                    return df
            except Exception as e:
                print(f"Error parsing stats for {url}: {e}")
                continue

    print(f"⚠️ Team Stats table not found in: {url}")
    return None

def process_week(year, week):
    """Aggregate team stats for all games in a given week."""
    boxscore_urls = get_boxscore_links(year, week)
    all_games = []

    for url in boxscore_urls:
        print(f"🔍 Processing: {url}")
        df = extract_team_stats(url)
        if df is not None:
            all_games.append(df)

    if not all_games:
        print("🚫 No team stats found for this week.")
        return

    full_df = pd.concat(all_games, ignore_index=True)
    output_dir = "CSV"
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"NFL_Stats_{year}_Week_{week}.csv")
    full_df.to_csv(filename, index=False)
    print(f"✅ All team stats saved to: {filename}")

def main():
    parser = argparse.ArgumentParser(description="Extract weekly NFL 'Team Stats' tables from Pro-Football-Reference.")
    parser.add_argument("year", type=int, help="NFL season year (e.g., 2023)")
    parser.add_argument("week", type=int, help="Week number (1–18)")
    args = parser.parse_args()
    process_week(args.year, args.week)

if __name__ == "__main__":
    main()
