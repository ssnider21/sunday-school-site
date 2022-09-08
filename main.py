from flask import Flask, render_template
from sunday_school.league import SundaySchool, Team
from leeger.league_loader import SleeperLeagueLoader
from leeger.model.league import League, Year
# from leeger.calculator.year_calculator import GameOutcomeYearCalculator, PointsScoredYearCalculator, \
# SingleScoreYearCalculator, ScoringShareYearCalculator, ScoringStandardDeviationYearCalculator, AWALYearCalculator, PlusMinusYearCalculator
from leeger.model.stat.YearStatSheet import YearStatSheet
from leeger.util.stat_sheet import yearStatSheet
from sleeper.api import LeagueAPIClient
from sleeper.enum import Sport
from sleeper.model import League, Roster, User, Matchup, PlayoffMatchup, Transaction, TradedPick, SportState, LeagueSettings
import pandas as pd
from decimal import *

import base64
from io import BytesIO
from matplotlib.figure import Figure

app = Flask(__name__)

# pd.options.display.float_format = '{:.2f}'.format

sleeperLeagueLoader = SleeperLeagueLoader("854402777273720832", [2021])
league = sleeperLeagueLoader.loadLeague()

x = league.years[0]

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

yearstats = yearStatSheet(x, onlyRegularSeason=True).__dict__
ys_with_nn = {}
for stat, d in yearstats.items():
    ys_with_nn[stat] = nicknames(d)

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


@app.route('/')
def index():
    l = SundaySchool()
    h = l.get_roster_season_projections()
    return render_template("index.html", league=h, tables=tables, full_table=html, power=pwr_styled)

@app.route('/team_breakdowns')
def team_breakdowns():
    return render_template("team_breakdowns.html", league=SundaySchool())