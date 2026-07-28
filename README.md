# IPL Analytics Dashboard

Interactive Streamlit dashboard built for the Data Visualization final project. Explores IPL
match, delivery, player, and season data across four themed tabs, with season and team
filters that apply throughout.

**Live app:** _add your Streamlit Community Cloud URL here after deploying_

## Tabs

- **Overview** — batting-first vs. chasing win rate over time, stage outcomes, win margins by city
- **Toss & Venue** — toss advantage by venue, team toss-dependency, day/night scoring by venue
- **Player Performance** — auction price vs. runs scored, capped vs. uncapped strike-rate trend
- **Bowling Matchups** — bowler-vs-opposition wicket heatmap, death-overs economy vs. wickets

## Project structure

```
.
├── app.py                  # Streamlit app
├── requirements.txt
├── data/
│   ├── matches.csv
│   ├── deliveries.csv
│   ├── players.csv
│   └── seasons.csv
└── README.md
```

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Push this repo to a **public** GitHub repository.
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in, and click **New app**.
3. Point it at this repo, branch `main`, main file `app.py`.
4. Deploy — you'll get a public URL to submit alongside the repo link.

## Data

IPL ball-by-ball deliveries, match results, player profiles, and season summaries. See the
companion analysis notebook (`IPL_Final_Project_Analysis.ipynb`) for the full 12-question
exploratory analysis this dashboard draws its curated subset from.
