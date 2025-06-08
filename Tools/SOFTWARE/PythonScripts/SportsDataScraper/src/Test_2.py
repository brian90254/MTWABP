import requests
from bs4 import BeautifulSoup

url = 'https://www.espn.com/nfl/game/_/gameId/401547382'
headers = {'User-Agent': 'Mozilla/5.0'}
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

teams = soup.select('span.abbrev')
scores = soup.select('div.ScoreCell__Score')

for team, score in zip(teams, scores):
    print(f"{team.text}: {score.text}")
