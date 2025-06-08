import requests
from bs4 import BeautifulSoup

url = 'https://www.pro-football-reference.com/boxscores/202309070kan.htm'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
}

response = requests.get(url, headers=headers)
print(response.text[:2000])  # Show first 1000 chars
soup = BeautifulSoup(response.text, 'html.parser')

# Find the scorebox div
scorebox = soup.find('div', class_='scorebox')
if not scorebox:
    print("Scorebox not found.")
else:
    team_names = [tag.get_text(strip=True) for tag in scorebox.find_all('strong')]
    scores = [tag.get_text(strip=True) for tag in scorebox.find_all('div', class_='score')]

    if len(team_names) == 2 and len(scores) == 2:
        print(f"{team_names[0]}: {scores[0]}")
        print(f"{team_names[1]}: {scores[1]}")
    else:
        print("Could not extract two teams and two scores.")
