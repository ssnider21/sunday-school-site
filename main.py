from flask import Flask, render_template
from sunday_school.league import SundaySchool, Team
from leeger.league_loader import SleeperLeagueLoader
from leeger.model.league import League, Year
from leeger.calculator.year_calculator import GameOutcomeYearCalculator, PointsScoredYearCalculator, \
SingleScoreYearCalculator, ScoringShareYearCalculator, ScoringStandardDeviationYearCalculator, AWALYearCalculator, PlusMinusYearCalculator
from leeger.model.stat.YearStatSheet import YearStatSheet
from leeger.util.stat_sheet import yearStatSheet
from sleeper.api import LeagueAPIClient
from sleeper.enum import Sport
from sleeper.model import League, Roster, User, Matchup, PlayoffMatchup, Transaction, TradedPick, SportState, LeagueSettings
import pandas as pd
import numpy as np
from decimal import *

import base64
from io import BytesIO
from matplotlib.figure import Figure

import json
import plotly
import plotly.express as px

from pprint import pprint as pp

app = Flask(__name__)

# pd.options.display.float_format = '{:.2f}'.format

sleeperLeagueLoader = SleeperLeagueLoader("854402777273720832", [2021])
league = sleeperLeagueLoader.loadLeague()

x = league.years[0]

# pp(x)
team_map = {}
for team in x.teams:
    team_map[team.id] = team.name

def nicknames(d):
    nd = {}
    for x in d:
        if isinstance(d[x], Decimal) or isinstance(d[x], float):
            # nd[team_map.get(x)] = d[x].quantize(Decimal('.01'), rounding=ROUND_UP)
            nd[team_map.get(x)] = float(d[x])
        else:
            nd[team_map.get(x)] = int(d[x])
    return nd

def nested_nicknames(d):
    nd = {}
    for x in d:
        nd[team_map.get(x)] = {}
        for s in d.get(x):
            if isinstance(d[x][s], Decimal) or isinstance(d[x][s], float):
                # nd[team_map.get(x)] = d[x].quantize(Decimal('.01'), rounding=ROUND_UP)
                nd[team_map.get(x)][s] = float(d[x][s])
            else:
                nd[team_map.get(x)][s] = int(d[x][s])
    return nd

yearstats = yearStatSheet(x, onlyRegularSeason=True).__dict__
ys_with_nn = {}
for stat, d in yearstats.items():
    ys_with_nn[stat] = nicknames(d)

new_ys_with_nn = {}
for i in range(1, 14):
    temp_yearstats = yearStatSheet(x, onlyRegularSeason=True, weekNumberEnd=i).__dict__
    new_ys_with_nn[i] = {}
    for stat, d in temp_yearstats.items():
        new_ys_with_nn[i][stat] = nicknames(d)
# pp(new_ys_with_nn)
w_pr = {}
for i in range(1, 14):
    w_pr[i] = {}
    for team in x.teams:
        w_pr[i][team.name] = {}
final = pd.DataFrame()
# final.set_index([team.name for team in x.teams])
for i in range(1, 14):
    for stat, d in new_ys_with_nn.get(i).items():
        if stat in set(["wal", "awal", "smartWins", "pointsScored", "scoringStandardDeviation", "overallWins"]):
            for team in d:
                w_pr[i][team][stat] = d.get(team)
# pp(w_pr)
    test_pwr = pd.DataFrame.from_dict(w_pr[i], orient='index')
    # pp(test_pwr)
    test_pwr["wal_rank"] = test_pwr["wal"].rank(ascending=False)
    test_pwr["awal_rank"] = test_pwr["awal"].rank(ascending=False)
    test_pwr["smartWins_rank"] = test_pwr["smartWins"].rank(ascending=False)
    test_pwr["pointsScored_rank"] = test_pwr["pointsScored"].rank(ascending=False)
    test_pwr["scoringStandardDeviation_rank"] = test_pwr["scoringStandardDeviation"].rank()
    test_pwr["overallWins_rank"] = test_pwr["overallWins"].rank(ascending=False)
    test_pwr[f"Power Rank {i}"] = test_pwr.apply(lambda row: ((3*row.wal_rank) + row.awal_rank + row.smartWins_rank + row.pointsScored_rank + row.scoringStandardDeviation_rank + row.overallWins_rank)/8, axis=1)
    test_pwr[f"Relative Power Rank {i}"] = test_pwr[f"Power Rank {i}"].rank()
    # pp(test_pwr)
    final[f"Relative Power Rank {i}"] = test_pwr[f"Relative Power Rank {i}"]

df = pd.DataFrame(ys_with_nn, columns=yearstats.keys())
html = df.style.format(lambda x: f'{x:,.3f}' if isinstance(x, float) else f'{x}').set_table_attributes('class="w-auto table allstats"').set_table_styles([dict(selector='th', props=[('text-align', 'center')])]).background_gradient(cmap='RdYlGn').to_html()

tables = []
for stat, d in ys_with_nn.items():
    df = pd.DataFrame.from_dict(d, orient='index', columns=[stat])
    styled = df.style.format(lambda x: f'{x:,.3f}' if isinstance(x, float) else f'{x}').set_table_attributes('class="table"').set_table_styles([dict(selector='th', props=[('text-align', 'center')])]).background_gradient(cmap='RdYlGn').to_html()
    tables.append(styled)

pr = {}
for team in x.teams:
    pr[team.name] = {}
for stat, d in ys_with_nn.items():
    if stat in set(["wal", "awal", "smartWins", "pointsScored", "scoringStandardDeviation", "overallWins"]):
        for team in d:
            pr[team][stat] = d.get(team)
pwr = pd.DataFrame.from_dict(pr, orient='index')
pwr["wal_rank"] = pwr["wal"].rank(ascending=False)
pwr["awal_rank"] = pwr["awal"].rank(ascending=False)
pwr["smartWins_rank"] = pwr["smartWins"].rank(ascending=False)
pwr["pointsScored_rank"] = pwr["pointsScored"].rank(ascending=False)
pwr["scoringStandardDeviation_rank"] = pwr["scoringStandardDeviation"].rank()
pwr["overallWins_rank"] = pwr["overallWins"].rank(ascending=False)
pwr["Power Rank"] = pwr.apply(lambda row: ((3*row.wal_rank) + row.awal_rank + row.smartWins_rank + row.pointsScored_rank + row.scoringStandardDeviation_rank + row.overallWins_rank)/8, axis=1)
pwr_styled =  pwr.style.format(lambda x: f'{x:,.3f}' if isinstance(x, float) else f'{x}').set_table_attributes('class="table"').set_table_styles([dict(selector='th', props=[('text-align', 'center')])]).hide_columns(["wal_rank", "awal_rank", "smartWins_rank", "pointsScored_rank", "scoringStandardDeviation_rank", "overallWins_rank"]).background_gradient(cmap='RdYlGn').to_html()

def create_stacked_bars(ss):
    ss = nested_nicknames(ss)
    labels = ss.keys()
    qb = np.array([ss.get(x).get("QB") for x in labels])
    rb =  np.array([ss.get(x).get("RB") for x in labels])
    wr =  np.array([ss.get(x).get("WR") for x in labels])
    te =  np.array([ss.get(x).get("TE") for x in labels])
    k =  np.array([ss.get(x).get("K") for x in labels])
    defense = np.array([ss.get(x).get("DEF") for x in labels])
    # width = 0.35       # the width of the bars: can also be len(x) sequence
    fig = Figure()
    ax = fig.subplots()
    ax.bar(labels, qb, label='QB')
    ax.bar(labels, rb, bottom=qb, label='RB')
    ax.bar(labels, wr, bottom=qb+rb, label='WR')
    ax.bar(labels, te, bottom=qb+rb+wr, label='TE')
    ax.bar(labels, k, bottom=qb+rb+wr+te, label='K')
    ax.bar(labels, defense, bottom=qb+rb+wr+te+k, label='DEF')
    ax.set_ylabel('Scores')
    ax.set_title('Scores by group and gender')
    ax.set_xticklabels(labels, rotation=30, ha='right')
    ax.legend()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=960)
    # Embed the result in the html output.
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    return f'<img src="data:image/png;base64,{data}"/ class="img-fluid">'

def get_fig():
    # Generate the figure **without using pyplot**.
    fig = Figure()
    ax = fig.subplots()
    ax.plot([1, 2])
    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format="png")
    # Embed the result in the html output.
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    return f"<img src='data:image/png;base64,{data}'/>"

def plotly_bar(ss):
    df = pd.DataFrame.from_dict(nested_nicknames(ss), orient='index')
    fig = px.bar(df, x=df.index, y=[c for c in df.columns])
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON

def plotly_line(df):
    pd.options.plotting.backend = "plotly"
    fig = df.T.plot()
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON


@app.route('/')
def index():
    l = SundaySchool()
    h = l.get_roster_season_projections()
    return render_template("index.html", league=h, tables=tables, full_table=html, power=pwr_styled, pr_chart=plotly_line(final))

@app.route('/team_breakdowns')
def team_breakdowns():
    return render_template("team_breakdowns.html", league=SundaySchool())

@app.route('/scoring_share')
def scoring_share():
    ss = PointsScoredYearCalculator.getPointsScoredByPosition(x, onlyRegularSeason=True)
    return render_template("scoring_share.html", graphJSON=plotly_bar(ss))