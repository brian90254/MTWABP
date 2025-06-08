import requests
from bs4 import BeautifulSoup, Comment
import pandas as pd
import argparse
import os

def extract_team_stats(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')

    # Search for the Team Stats table inside HTML comments
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    for comment in comments:
        if 'Team Stats' in comment:
            try:
                comment_soup = BeautifulSoup(comment, 'html.parser')
                table = comment_soup.find('table')
                if table:
                    df = pd.read_html(str(table))[0]
                    return df
            except Exception as e:
                print(f"Error parsing table: {e}")
                continue

    print("⚠️ Team Stats table not found.")
    return None

def save_to_csv(df, url):
    # Extract a unique identifier from the URL
    game_id = url.strip('/').split('/')[-1].replace('.htm', '')
    output_dir = "CSV"
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"{game_id}_TeamStats.csv")
    df.to_csv(filename, index=False)
    print(f"✅ Team stats saved to: {filename}")

def main():
    parser = argparse.ArgumentParser(description="Extract 'Team Stats' table from a Pro-Football-Reference box score URL.")
    parser.add_argument("url", type=str, help="Full box score URL (e.g., https://www.pro-football-reference.com/boxscores/202309070kan.htm)")
    args = parser.parse_args()

    print(f"🔍 Fetching team stats from: {args.url}")
    df = extract_team_stats(args.url)

    if df is not None:
        print("\n📊 Team Stats Table Preview:\n")
        print(df.head())
        save_to_csv(df, args.url)
    else:
        print("🚫 Failed to extract team stats.")

if __name__ == "__main__":
    main()
